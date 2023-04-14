import re
import socket

from whois_info import WhoisInfo
from abc import ABC, abstractmethod


def _get_value(data: dict, key: str):
    try:
        return data[key]
    except Exception:
        return ''


class WhoisConn(ABC):
    def __init__(self, addr):
        self._whois_addr = addr
        self._port = 43
        self._parse_reg = re.compile(
            r'^([\w-]+?): +([^\n#]+)#?[\n]*', re.MULTILINE)
        self._timeout = 2
        self._socket = socket.socket()

    def connect(self):
        self._socket = socket.socket()
        self._socket.settimeout(self._timeout)
        self._socket.connect((self._whois_addr, self._port))

    def close(self):
        self._socket.close()

    def get_whois_info(self, address) -> WhoisInfo:
        data = self._get_data(address)
        if self._response_is_correct(data):
            dict_data = dict(self._parse_reg.findall(data))
            return self._get_whois_info(address, dict_data)
        else:
            None

    @abstractmethod
    def _response_is_correct(self, data):
        return False

    def _get_data(self, address: str) -> str:
        if isinstance(address, str):
            address = address.encode('utf8')
        self._socket.send(self._query(address))
        data = []
        while True:
            try:
                byte_buffer = self._socket.recv(4096)
            except socket.timeout:
                break
            if len(byte_buffer) == 0:
                break
            data.append(byte_buffer)
        result_data = b''.join(data)
        return result_data.decode('utf8', errors='ignore')

    @abstractmethod
    def _query(self, address: bytes):
        return b'-Bk ' + address + b'\r\n'

    @abstractmethod
    def _get_whois_info(self, ip, data: dict):
        return None


class ConnToARIN(WhoisConn):
    def __init__(self):
        super().__init__('whois.arin.net')

    def get_whois_info(self, address) -> WhoisInfo:
        self.connect()
        result = super().get_whois_info(address)
        self.close()
        return result

    def _query(self, address: bytes):
        return b'n ' + address + b'\r\n'

    def _response_is_correct(self, data):
        return 'Allocated to' not in data \
               and 'Transferred to LACNIC' not in data \
               and 'This IP address range is under LACNIC responsibility' not in data

    def _get_whois_info(self, ip, data: dict):
        return WhoisInfo(
            source=self._whois_addr.split('.')[1],
            ip=ip,
            net=_get_value(data, 'CIDR'),
            as_num=_get_value(data, 'OriginAS'),
            country_code=_get_value(data, 'Country'),
            isp=_get_value(data, 'Organization'))


class ConnToRIPE(WhoisConn):
    def __init__(self):
        super().__init__('whois.ripe.net')
        super().connect()

    def _query(self, address: bytes):
        return b'-Bk ' + address + b'\r\n'

    def close(self):
        self._socket.send(b'-k\r\n')
        super().close()

    def _response_is_correct(self, data):
        return 'NON-RIPE-NCC-MANAGED-ADDRESS-BLOCK' not in data

    def _get_whois_info(self, ip, data: dict):
        return WhoisInfo(
            source=_get_value(data, 'source') or self._whois_addr.split('.')[1],
            ip=ip,
            net=_get_value(data, 'inetnum'),
            as_num=_get_value(data, 'origin'),
            country_code=_get_value(data, 'country'),
            isp=_get_value(data, 'org-name') or _get_value(data, 'mnt-by'))


class ConnToAPNIC(WhoisConn):
    def __init__(self):
        super().__init__('whois.apnic.net')
        super().connect()

    def _query(self, address: bytes):
        return b'-Bk ' + address + b'\r\n'

    def close(self):
        self._socket.send(b'-k\r\n')
        super().close()

    def _response_is_correct(self, data):
        return 'This network range is not allocated to APNIC.' not in data \
               and 'Not allocated by APNIC' not in data

    def _get_whois_info(self, ip, data: dict):
        return WhoisInfo(
            source=self._whois_addr.split('.')[1],
            ip=ip,
            net=_get_value(data, 'inetnum'),
            as_num=_get_value(data, 'origin'),
            country_code=_get_value(data, 'country'),
            isp=_get_value(data, 'mnt-lower') or _get_value(data, 'mnt-by'))


class ConnToLACNIC(WhoisConn):
    def __init__(self):
        super().__init__('whois.lacnic.net')

    def get_whois_info(self, address) -> WhoisInfo:
        self.connect()
        result = super().get_whois_info(address)
        self.close()
        return result

    def _query(self, address: bytes):
        return address + b'\r\n'

    def _response_is_correct(self, data):
        return True

    def _get_whois_info(self, ip, data: dict):
        return WhoisInfo(
            source=_get_value(data, 'source') or self._whois_addr.split('.')[1],
            ip=ip,
            net=_get_value(data, 'inetnum'),
            as_num=_get_value(data, 'aut-num'),
            country_code='',
            isp='')


class ConnToAFRINIC(WhoisConn):
    def __init__(self):
        super().__init__('whois.afrinic.net')
        super().connect()

    def _query(self, address: bytes):
        return b'-Bk ' + address + b'\r\n'

    def close(self):
        self._socket.send(b'-k\r\n')
        super().close()

    def _response_is_correct(self, data):
        return 'The WHOIS is temporary unable to query' not in data

    def _get_whois_info(self, ip, data: dict):
        return WhoisInfo(
            source=_get_value(data, 'source'),
            ip=ip,
            net=_get_value(data, 'route'),
            as_num=_get_value(data, 'origin'),
            country_code=_get_value(data, 'country'),
            isp='')
