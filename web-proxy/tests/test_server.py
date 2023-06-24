from asyncio import StreamReader
from asyncio.base_events import Server
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

from features.collector import PasswordCollector
from proxy.connection import ProxyConnection
from proxy.server import ProxyServer
from tests.test_connection import ProxyConnectionAsyncTests


class ServerAsyncTests(IsolatedAsyncioTestCase):

    @staticmethod
    def get_server():
        with patch.object(PasswordCollector, '__init__', return_value=None):
            return ProxyServer(host='localhost',
                               port=8080,
                               buffer_size=4096,
                               users=100)

    @patch('asyncio.start_server')
    async def test_run(self, mock_start_server):
        server = self.get_server()
        await server.run()
        mock_start_server.assert_called_once_with(
            client_connected_cb=server._handle_client,
            host='localhost',
            port=8080,
            backlog=100)

    async def test_close(self):
        server = self.get_server()
        server._set_clients = {ProxyConnectionAsyncTests().get_connection()}
        with patch.object(Server, '__init__',
                          return_value=None) as mock_server, \
                patch.object(Server, 'close') as mock_close_server, \
                patch.object(Server, 'wait_closed') as mock_wait, \
                patch.object(ProxyConnection, 'close') as mock_close_conn:
            server._server = Server()
            await server.close()

        mock_server.assert_called_once()
        mock_close_server.assert_called_once()
        mock_wait.assert_called_once()
        mock_wait.assert_awaited()
        mock_close_conn.assert_called_once()
        mock_close_conn.assert_awaited()

    async def test_handle_client(self):
        server = self.get_server()
        self.assertEqual(0, len(server._set_clients))
        reader = StreamReader()
        writer = ProxyConnectionAsyncTests.get_writer()
        with patch.object(ProxyConnection, '__init__',
                          return_value=None) as mock_conn, \
                patch.object(ProxyConnection, '__hash__',
                             return_value=0) as mock_hash, \
                patch.object(ProxyConnection, 'run') as mock_run, \
                patch.object(ProxyConnection, 'close') as mock_close:
            await server._handle_client(reader, writer)

        mock_conn.assert_called_once_with(
            client_reader=reader,
            client_writer=writer,
            buffer_size=4096,
            close_hook=server._set_clients.remove,
            password_collector=server._password_collector
        )
        self.assertEqual(1, len(server._set_clients))
        mock_run.assert_called_once()
        mock_run.assert_awaited()
        mock_hash.assert_called_once()
        mock_close.assert_called()
        mock_close.assert_awaited()
