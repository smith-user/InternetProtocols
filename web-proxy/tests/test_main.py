from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

from proxy.server import ProxyServer
from proxy.__main__ import main


class MainTests(IsolatedAsyncioTestCase):

    @patch.object(ProxyServer, '__init__', return_value=None)
    @patch.object(ProxyServer, 'run')
    @patch.object(ProxyServer, 'close')
    async def test_main(self, mock_close, mock_run, mock_init):
        await main(host='localhost',
                   port=12345,
                   users=100,
                   buffer_size=1024)
        mock_init.assert_called_once_with(
            host='localhost',
            port=12345,
            users=100,
            buffer_size=1024
        )
        mock_run.assert_called_once()
        mock_run.assert_awaited()
        mock_close.assert_called_once()
        mock_close.assert_awaited()
