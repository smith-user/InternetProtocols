import argparse
import asyncio
import logging

from proxy.errors import ProxyError
from proxy.server import ProxyServer

parser = argparse.ArgumentParser(prefix_chars='-',
                                 description='Web-proxy')
parser.add_argument('--host', default='localhost', type=str,
                    help='Start proxy on host, default=localhost')
parser.add_argument('-p', '--port', default=8080, type=int,
                    help='Start proxy on port, default=8080')
parser.add_argument('-u', '--users', default=100, type=int,
                    help='Set count of users, default=100')
parser.add_argument('-b', '--buffer', default=4096, type=int,
                    help='Set buffer size, default=4096')
parser.add_argument('-t', '--timeout', default=1, type=int,
                    help='Set timeout wait request, default=1')

logging.basicConfig(format='%(levelname)s - %(name)s - '
                           '%(asctime)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.INFO)

logger = logging.getLogger('main')


async def main(host: str, port: int, users: int, buffer_size: int):
    proxy_server = None
    try:
        proxy_server = ProxyServer(host=host,
                                   port=port,
                                   users=users,
                                   buffer_size=buffer_size)
        await proxy_server.run()
    except ProxyError as exception:
        logger.warning(f'{exception.message}')
        exit(1)
    finally:
        if proxy_server:
            await proxy_server.close()


if __name__ == '__main__':
    try:
        args = parser.parse_args()
        asyncio.run(main(host=args.host,
                         port=args.port,
                         users=args.users,
                         buffer_size=args.buffer))
    except KeyboardInterrupt:
        logger.warning(f'KeyboardInterrupt')
