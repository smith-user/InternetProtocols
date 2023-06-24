import socket
import unittest
from asyncio import StreamWriter, StreamReader
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch, MagicMock

from features.collector import PasswordCollector
from proxy.connection import ProxyConnection, get_id
from proxy.errors import UnresolvedRequest
from proxy.httpparser import HTTPRequest, HTTPResponse
from sslcert import CertificateCreator


class ProxyConnectionSyncTests(unittest.TestCase):

    def test_id(self):
        id_iter = get_id()
        for i in range(1, 10):
            self.assertEqual(i, next(id_iter))


class ProxyConnectionAsyncTests(IsolatedAsyncioTestCase):

    def get_connection(self):
        with patch.object(CertificateCreator, '__init__',
                          return_value=None), \
                patch.object(PasswordCollector, '__init__',
                             return_value=None):
            connection = ProxyConnection(
                buffer_size=4096,
                client_reader=StreamReader(),
                client_writer=self.get_writer(),
                close_hook=MagicMock(),
                password_collector=PasswordCollector())

            connection._w_target = self.get_writer()
            return connection

    @staticmethod
    def get_writer():
        with patch.object(StreamWriter, '__init__',
                          return_value=None), \
                patch.object(StreamWriter, 'get_extra_info'), \
                patch.object(StreamWriter, 'close'), \
                patch.object(StreamWriter, 'wait_closed'):
            return StreamWriter()

    async def test_init(self):
        connection = self.get_connection()
        self.assertEqual(connection.id, hash(connection))
        self.assertFalse(connection._closed)

    async def test_run(self):
        connection = self.get_connection()
        with patch.object(ProxyConnection, '_create_connection') as mock:
            await connection.run()
        mock.assert_called_once()

    async def test_run_exc(self):
        connection = self.get_connection()
        with patch.object(ProxyConnection, '_create_connection',
                          side_effect=KeyboardInterrupt()) as mock, \
                self.assertRaises(KeyboardInterrupt):
            await connection.run()
        mock.assert_called_once()

    async def test_close(self):
        connection = self.get_connection()
        with patch.object(ProxyConnection, '_close_connections') as mock:
            await connection.close()
        mock.assert_called_once()
        connection._close_hook.assert_called_once()
        self.assertTrue(connection._closed)

    async def test_close_connections(self):
        connection = self.get_connection()
        with patch.object(StreamWriter, 'close') as mock1, \
                patch.object(StreamWriter, 'wait_closed') as mock2:
            await connection._close_connections()
        mock1.assert_called()
        mock2.assert_called()

    async def test_request_cb(self):
        connection = self.get_connection()
        request = HTTPRequest()
        addr = 'addr'
        with patch.object(PasswordCollector, 'add_userdata') as mock_add, \
                patch.object(StreamWriter, 'get_extra_info',
                             return_value=addr) as mock_get:
            self.assertEqual(request, connection._request_cb(request))
        mock_get.assert_called()
        mock_add.assert_called_once_with(addr, request)

    async def test_response_cb(self):
        connection = self.get_connection()
        response = HTTPResponse()
        self.assertEqual(response, connection._response_cb(response))

    async def test_http_exchange_server_side(self):
        connection = self.get_connection()
        source = StreamReader()
        target = self.get_writer()
        httprequest = HTTPRequest(method='GET', proto='HTTP/1.1', path='/test')
        with patch.object(ProxyConnection, '_request_cb',
                          return_value=httprequest) as mock_cb, \
                patch.object(StreamWriter, 'is_closing',
                             return_value=False) as mock_closing, \
                patch.object(StreamWriter, 'write') as mock_write, \
                patch.object(StreamWriter, 'drain') as mock_drain, \
                patch.object(HTTPRequest, 'from_stream') as mock_parser, \
                patch.object(HTTPRequest, 'del_proxy_head') as mock_del_head:
            self.assertTrue(await connection._http_exchange(source=source,
                                                            target=target,
                                                            server_side=True))
        mock_cb.assert_called_once()
        mock_closing.assert_called()
        mock_write.assert_called_once_with(bytes(httprequest))
        mock_drain.assert_called_once()
        mock_drain.assert_awaited()
        mock_parser.assert_called_once_with(source)
        mock_del_head.assert_called_once()

    async def test_http_exchange_client_side(self):
        connection = self.get_connection()
        source = StreamReader()
        target = self.get_writer()
        httpresponse = HTTPResponse(proto='HTTP/1.1', code=200, message='OK')
        with patch.object(ProxyConnection, '_response_cb',
                          return_value=httpresponse) as mock_cb, \
                patch.object(StreamWriter, 'is_closing',
                             return_value=False) as mock_closing, \
                patch.object(StreamWriter, 'write') as mock_write, \
                patch.object(StreamWriter, 'drain') as mock_drain, \
                patch.object(HTTPResponse, 'from_stream') as mock_parser:
            self.assertTrue(await connection._http_exchange(source=source,
                                                            target=target,
                                                            server_side=False))
        mock_cb.assert_called_once()
        mock_closing.assert_called()
        mock_write.assert_called_once_with(bytes(httpresponse))
        mock_drain.assert_called_once()
        mock_drain.assert_awaited()
        mock_parser.assert_called_once_with(source)

    async def test_create_connection_http(self):
        connection = self.get_connection()
        httprequest = HTTPRequest(method='GET', proto='HTTP/1.1', path='/test',
                                  host='host', port=12345)
        with patch.object(StreamWriter, 'write') as mock_write, \
                patch.object(StreamWriter, 'get_extra_info') as mock_get, \
                patch.object(StreamWriter, 'drain') as mock_drain, \
                patch.object(HTTPRequest, 'from_stream',
                             return_value=httprequest) as mock_parser, \
                patch.object(ProxyConnection, '_http_exchange',
                             return_value=False) as mock_exchange, \
                patch('asyncio.open_connection',
                      return_value=(StreamReader(),
                                    self.get_writer())) as mock_open:
            await connection._create_connection()

        self.assertFalse(connection._https)
        mock_open.assert_called_once_with(
            host=httprequest.host,
            port=httprequest.port,
            family=socket.AF_INET)
        mock_get.assert_called_once_with('peername')
        mock_write.assert_called_once_with(bytes(httprequest))
        mock_drain.assert_called_once()
        mock_drain.assert_awaited()
        mock_parser.assert_called_once_with(source=connection._reader)
        mock_exchange.assert_called()

    async def test_create_connection_https(self):
        connection = self.get_connection()
        httprequest = HTTPRequest(method='CONNECT', proto='HTTP/1.1',
                                  path='/test', host='host', port=12345)
        with patch.object(StreamWriter, 'get_extra_info') as mock_get, \
                patch.object(HTTPRequest, 'from_stream',
                             return_value=httprequest) as mock_parser, \
                patch.object(ProxyConnection, '_http_exchange',
                             return_value=False) as mock_exchange, \
                patch.object(ProxyConnection, '_open_tls') as mock_tls, \
                patch('asyncio.open_connection',
                      return_value=(StreamReader(),
                                    self.get_writer())) as mock_open:
            await connection._create_connection()

        self.assertTrue(connection._https)
        mock_open.assert_called_once_with(
            host=httprequest.host,
            port=httprequest.port,
            family=socket.AF_INET)
        mock_get.assert_called_once_with('peername')
        mock_tls.assert_called_once_with(target_host=httprequest.host)
        mock_parser.assert_called_once_with(source=connection._reader)
        mock_exchange.assert_called()

    async def test_create_connection_exc(self):
        connection = self.get_connection()
        httprequest = HTTPRequest(method=None, proto='HTTP/1.1',
                                  path=None, host='host', port=12345)
        with patch.object(StreamWriter, 'get_extra_info') as mock_get, \
                patch.object(HTTPRequest, 'from_stream',
                             return_value=httprequest) as mock_parser, \
                self.assertRaises(UnresolvedRequest):
            await connection._create_connection()

        mock_get.assert_called_once_with('peername')
        mock_parser.assert_called_once_with(source=connection._reader)
