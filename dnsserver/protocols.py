import asyncio


class DNSServerProtocol:
    def __init__(self, callback):
        self.transport = None
        self.callback = callback

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        print(f'New client {addr}.')
        loop = asyncio.get_running_loop()
        loop.create_task(self.callback(self.transport, data, addr))

    def error_received(self, exc):
        print('DNSServerProtocol: Error received. ', exc)

    def connection_lost(self, exc):
        print('DNSServerProtocol: Connection lost.')


class DNSClientProtocol:
    def __init__(self, data, response_received):
        self.data = data
        self.response_received = response_received
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport
        self.transport.sendto(self.data)

    def datagram_received(self, data, addr):
        print(f'Response from {addr}')
        self.response_received.set_result(data)

    def error_received(self, exc):
        print('DNSClientProtocol: Error received. ', exc)

    def connection_lost(self, exc):
        print('DNSClientProtocol: Connection lost.')
