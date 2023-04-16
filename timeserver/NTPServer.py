import socket

from NTPPacket import *


class StratumError(Exception):
    def __init__(self):
        super().__init__('StratumError')


class NTPServer:
    def __init__(self, host: str, port: int, sec: int, users: int):
        self.dn_stratum = 'time.windows.com'
        self.ip_stratum = socket.gethostbyname(self.dn_stratum)
        self.host = host
        self.port = port
        self.property_sec = sec
        self.users = users

    def run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.bind((self.host, self.port))
            while True:
                self.new_conn(s)

    def new_conn(self, server: socket):
        data, addr = server.recvfrom(48)
        time_receive = time.time()
        print(f'Новое соединение {addr}')

        request_from_clinet = NTPPacket()
        request_from_clinet.unpack(data)

        response_from_server, arrive_time = self.get_response(
            request_from_clinet.mode,
            request_from_clinet.version)

        if response_from_server.stratum >= 15:
            raise StratumError()

        time_diff = response_from_server.get_time_different(arrive_time + FORMAT_DIFF)
        print(f'Разница времени сервера и времени у стратума: {time_diff}.')
        response_to_client = NTPPacket(
            leap_indicator=response_from_server.leap_indicator,
            version=response_from_server.version,
            mode=response_from_server.mode,
            stratum=response_from_server.stratum + 1,
            pool=response_from_server.pool,
            precision=response_from_server.precision,
            root_delay=response_from_server.root_delay,
            root_dispersion=response_from_server.root_dispersion,
            ref_id=self.get_ref_id(),
            reference=response_from_server.reference + self.property_sec,
            originate=request_from_clinet.transmit,
            receive=time_receive + FORMAT_DIFF + time_diff + self.property_sec,
            transmit=time.time() + FORMAT_DIFF + time_diff + self.property_sec
        )
        server.sendto(response_to_client.pack(), addr)

    def get_ref_id(self) -> int:
        buff = 0
        for part in self.ip_stratum.split('.'):
            buff = buff * 2 ** 8 + int(part)
        return buff

    def get_response(self, mode, version) -> (NTPPacket, int):
        print(f'Запрос к серверу {self.dn_stratum} ({self.ip_stratum}).')
        waiting_time = 5
        port = 123
        answer = NTPPacket()
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(waiting_time)
            request = NTPPacket(mode=mode, version=version)
            s.sendto(request.pack(), (self.ip_stratum, port))
            data = s.recv(48)
            arrive_time = time.time()
            answer.unpack(data)
        print(f'Ответ сервера {self.dn_stratum} ({self.ip_stratum}):')
        print(answer.to_display())
        print(f'----Arrive time: {arrive_time + FORMAT_DIFF}')
        return answer, arrive_time
