import asyncio
import socket
import ssl
import logging
from asyncio import StreamReader, StreamWriter

from proxy.errors import *
from proxy.httpparser import HTTPRequest, HTTPResponse, HTTPCode200
from sslcert.sslcreator import CertificateCreator
from sslcert.errors import SSlContextError


def get_id():
    i = 1
    while True:
        yield i
        i += 1


class ProxyConnection:
    _iter_id = iter(get_id())
    _logger = logging.getLogger('proxyConnection')

    def __init__(self,
                 buffer_size: int,
                 client_reader: StreamReader,
                 client_writer: StreamWriter,
                 password_collector,
                 close_hook):
        self._id = next(self._iter_id)
        self._buffer_size = buffer_size
        self._close_hook = close_hook
        self._reader: StreamReader = client_reader
        self._writer: StreamWriter = client_writer
        self._r_target: StreamReader = None
        self._w_target: StreamWriter = None
        self._https = False
        self._cert_creator = CertificateCreator()
        self._closed = False
        self._password_collector = password_collector

    @property
    def id(self):
        return self._id

    def __hash__(self):
        return self.id

    async def run(self):
        """
        :raise ConnectionException
        :return: None
        """
        try:
            await self._create_connection()
        except KeyboardInterrupt:
            self._logger.warning(f'KeyboardInterrupt')
            raise

    async def _create_connection(self):
        """
        :raise UnresolvedRequest
        :raise SSLHandshakeError
        :raise IllegalCertificate
        :raise SSLContextError
        :return:
        """
        addr = self._writer.get_extra_info('peername')
        self._logger.info(f'({self.id}) New client {addr}')
        request = await HTTPRequest().from_stream(source=self._reader)
        if request.method is None and request.path is None:
            raise UnresolvedRequest('')
        self._logger.info(f'({self.id}) {request.method} {request.path}')
        self._r_target, self._w_target = await asyncio.open_connection(
            host=request.host,
            port=request.port,
            family=socket.AF_INET
        )
        self._logger.info(f'({self.id}) Open TCP connection to {request.path}')
        if b'CONNECT' == request.method.encode():
            self._https = True
            await self._open_tls(target_host=request.host)
        else:
            self._https = False
            self._w_target.write(bytes(request))
            await self._w_target.drain()

        while True:
            results = await asyncio.gather(
                self._http_exchange(source=self._r_target,
                                    target=self._writer, server_side=False),
                self._http_exchange(source=self._reader,
                                    target=self._w_target, server_side=True)
            )
            if not any(results):
                break

    async def _open_tls(self, target_host):
        """
        :param target_host:
        :raise SSLHandshakeError
        :raise IllegalCertificate
        :raise SSLContextError
        :return:
        """
        await self._start_tls(stream=self._w_target,
                              context=ssl.create_default_context(),
                              server_side=False)
        try:
            cert: dict = self._w_target.get_extra_info('peercert')
        except ValueError:
            raise SSLHandshakeError('SSL handshake has not been done.')
        if not cert:
            raise IllegalCertificate('Certificate is null or empty')

        self._writer.write(bytes(HTTPCode200))
        await self._writer.drain()
        self._logger.info(
            f'({self.id}) HTTP/1.1 200 has been sent to the client')

        try:
            context = self._cert_creator.create_sslcontext(target_host, cert)
        except SSlContextError as e:
            self._logger.warning(f'({self.id}) {e.message}')
            raise

        await self._start_tls(self._writer, context=context, server_side=True)

    async def _start_tls(self, stream: StreamWriter,
                         context: ssl.SSLContext,
                         server_side: bool):
        """
        :param stream:
        :param context:
        :param server_side:
        :raise IllegalCertificate
        :return:
        """
        try:
            await stream.start_tls(sslcontext=context)
        except ssl.SSLCertVerificationError as exc:
            side = 'server_side' if server_side else 'client_side'
            self._logger.warning(
                f'({self.id}) SSLCertVerificationError was occurred ({side}).')
            raise IllegalCertificate(exc.verify_message)
        except ssl.SSLError as e:
            side = 'server_side' if server_side else 'client_side'
            self._logger.warning(f'({self.id}) SSLError was occured ({side})')
            raise SSLHandshakeError(f'{e.reason}')

    def _request_cb(self, request: HTTPRequest) -> HTTPRequest:
        addr = self._writer.get_extra_info('peername')
        self._password_collector.add_userdata(addr, request)
        return request

    def _response_cb(self, response: HTTPResponse) -> HTTPResponse:
        return response

    async def _http_exchange(self,
                             source: StreamReader,
                             target: StreamWriter,
                             server_side: bool) -> bool:
        if target.is_closing():
            return False
        if server_side:
            package = self._request_cb(await HTTPRequest().from_stream(source))
            package.del_proxy_head()
            self._logger.info(
                f'({self.id}) '
                f'HTTP: {package.method} {package.host}')
        else:
            package = self._response_cb(
                await HTTPResponse().from_stream(source))
            self._logger.info(
                f'({self.id}) '
                f'HTTP: {package.proto} {package.code} {package.message}')
        if target.is_closing():
            return False
        target.write(bytes(package))
        await target.drain()
        return True

    async def _close_connections(self):
        self._writer.close()
        if self._w_target:
            self._w_target.close()
            await asyncio.gather(
                self._writer.wait_closed(),
                self._w_target.wait_closed()
            )
        else:
            await self._writer.wait_closed()
        self._logger.info(f'({self.id}) Disconnected.')

    async def close(self):
        if not self._closed:
            self._closed = True
            await self._close_connections()
            self._close_hook(self)
            self._logger.info(f'({self.id}) Close connection object.')
