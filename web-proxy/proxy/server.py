import asyncio
import logging
import sys
import traceback
from asyncio import StreamReader, StreamWriter

from features.collector import PasswordCollector
from proxy.connection import ProxyConnection
from proxy.errors import ConnectionException


class ProxyServer:
    def __init__(self,
                 host: str,
                 port: int,
                 buffer_size: int,
                 users: int = 100):
        self._host = host
        self._port = port
        self._users = users
        self._buffer_size = buffer_size
        self._logger = logging.getLogger('proxyServer')
        self._server = None
        self._set_clients: set[ProxyConnection] = set()
        self._password_collector = PasswordCollector()

    async def run(self):
        self._server = await asyncio.start_server(
            client_connected_cb=self._handle_client,
            host=self._host,
            port=self._port,
            backlog=self._users)

        addrs = ', '.join(str(s.getsockname()) for s in self._server.sockets)
        self._logger.info(f'Serving on {addrs}')

        try:
            async with self._server:
                await self._server.serve_forever()
        except asyncio.exceptions.CancelledError:
            self._logger.warning(f'CancelledError was occurred.')
            return
        except Exception:
            t, v, tb = sys.exc_info()
            self._logger.warning(
                f' (run server) Exception was occurred \n'
                f'{repr(traceback.format_exception(v))}')
        except KeyboardInterrupt:
            self._logger.warning(f'KeyboardInterrupt')
            raise

    async def _handle_client(self, reader: StreamReader, writer: StreamWriter):
        connection = ProxyConnection(
            client_reader=reader,
            client_writer=writer,
            buffer_size=self._buffer_size,
            close_hook=self._set_clients.remove,
            password_collector=self._password_collector
        )
        self._set_clients.add(connection)
        try:
            await connection.run()
        except ConnectionException as e:
            self._logger.warning(f'({connection.id}) {e.message}')
        except Exception:
            t, v, tb = sys.exc_info()
            self._logger.warning(
                f'({connection.id}) Exception was occurred ({t})\n'
                f'{repr(traceback.format_exception(v))}')
        finally:
            await connection.close()

    async def close(self):
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        self._logger.info(f'The server is disabled.')
        self._logger.info(
            f'Closing clients\' connections (num={len(self._set_clients)}).')
        await asyncio.gather(
              *[client.close() for client in self._set_clients]
        )
        self._logger.info('All clients\' connections closed.')
