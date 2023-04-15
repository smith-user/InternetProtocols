import socket

from NTPPacket import *


class StratumError(Exception):
    def __init__(self):
        super().__init__('StratumError')


class NTPServer:
    def __init__(self, host: str, port: int, sec: int, users: int):
        self.ip_server = socket.gethostbyname('time.windows.com')
        self.host = host
        self.port = port
        self.property_sec = sec
        self.users = users

    def run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.bind((self.host, self.port))
            while True:
                self.new_conn(s, *s.recvfrom(48))

    def new_conn(self, server: socket, data: bytes, addr):
        print(f'Connection from {addr}')

        request_from_clinet = NTPPacket()
        time_receive = time.time()
        request_from_clinet.unpack(data)

        request_to_server = NTPPacket(
            mode=request_from_clinet.mode,
            version=request_from_clinet.version)
        response_from_server, arrive_time = self.get_response(request_to_server)

        if response_from_server.stratum >= 15:
            raise StratumError()

        time_diff = response_from_server.get_time_different(arrive_time + FORMAT_DIFF)
        response_to_client = NTPPacket(
            leap_indicator=response_from_server.leap_indicator,
            version=response_from_server.version,
            mode=response_from_server.mode,
            stratum=int(response_from_server.stratum) + 1,
            pool=response_from_server.pool,
            precision=response_from_server.precision,
            root_delay=response_from_server.root_delay,
            root_dispersion=response_from_server.root_dispersion,
            ref_id=self.ip_server,
            reference=response_from_server.reference + self.property_sec,
            originate=request_from_clinet.transmit,
            receive=time_receive + FORMAT_DIFF + time_diff + self.property_sec,
            transmit=time.time() + FORMAT_DIFF + time_diff + self.property_sec
        )
        server.sendto(response_to_client.pack(), addr)

    def get_response(self, request: NTPPacket) -> (NTPPacket, int):
        waiting_time = 5
        port = 123
        answer = NTPPacket()
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(waiting_time)
            s.sendto(request.pack(), (self.ip_server, port))
            data = s.recv(48)
            arrive_time = time.time()
            answer.unpack(data)
        return answer, arrive_time
