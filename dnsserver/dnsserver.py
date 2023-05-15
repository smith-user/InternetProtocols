import argparse
import asyncio

from entities import *
from protocols import DNSServerProtocol, DNSClientProtocol
from dnscache import Cache


class DNSServer:
    def __init__(self, addr, forwarder, cache_file):
        self._addr = addr
        self._forwarder = forwarder
        self._cache = Cache(cache_file)

    async def start(self):
        print(f'Starting DNS server {self._addr}')
        loop = asyncio.get_running_loop()
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: DNSServerProtocol(callback=self._send_answer),
            local_addr=self._addr)
        try:
            await asyncio.Event().wait()  # wait forever
        except asyncio.exceptions.CancelledError:
            print('\nKeyboardInterrupt')
        except Exception as e:
            print(f'Unexpected exception: {e}')
        finally:
            transport.close()
            print('Stop serving.')
            self.stop()

    async def _send_answer(self, transport, data, addr):
        package = await self._make_answer(data)
        print(f'Response to client:\n\t{str(package)}')
        transport.sendto(bytes(package), addr)

    async def _make_answer(self, request: bytes) -> DNSPackage:
        package = DNSPackage(request)
        print(f'Request from client:\n\t{str(package)}')
        from_cache = True
        for question in package.questions:
            cached_records = self._cache[question]
            if len(cached_records) == 0:
                response = await self._ask_forwarder(request)
                print(f'Response from {self._forwarder}:\n\t{str(response)}')
                self._cache.update(response.records)
                cached_records = self._cache[question]
                if len(cached_records) == 0:
                    continue
                from_cache = False
            if question.qtype == TYPE_SOA:
                package.authority.extend(cached_records)
            else:
                package.answers.extend(cached_records)
        if from_cache and len(list(package.records)) > 0:
            print('Resource records was loaded from cache.')
        package.flags = 0x8580
        return package

    async def _ask_forwarder(self, request) -> DNSPackage:
        loop = asyncio.get_running_loop()
        response_received = loop.create_future()
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: DNSClientProtocol(request, response_received),
            remote_addr=self._forwarder)
        try:
            await response_received
            data = response_received.result()
            return DNSPackage(data)
        finally:
            transport.close()

    def stop(self):
        self._cache.dump_cache()


parser = argparse.ArgumentParser(prefix_chars='-',
                                 description='DNS server')
parser.add_argument('--host', default='127.0.0.1', type=str,
                    help='Start proxy on host, default=127.0.0.1')
parser.add_argument('-s', '--server', type=str, default='8.8.8.8',
                    help='DNS server address.')
parser.add_argument('-c', '--cache',  type=str, default='cache',
                    help='Cache filename, default=cache')


async def main():
    args = parser.parse_args()
    await DNSServer(addr=(args.host, 53),
                    forwarder=(args.server, 53),
                    cache_file=args.cache).start()


if __name__ == '__main__':
    asyncio.run(main())
