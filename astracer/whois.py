from whois_conn import ConnToRIPE, ConnToARIN, ConnToAPNIC, ConnToLACNIC, ConnToAFRINIC
from whois_info import WhoisInfo


class WhoisDB:
    def __init__(self):
        self._whois_servers_conn = [
            ConnToRIPE(),    # Europe
            ConnToARIN(),    # Northern America
            ConnToAPNIC(),   # Asia Pacific
            ConnToAFRINIC(), # Africa
            ConnToLACNIC(),  # Latin America and the Carribean
        ]
        self._server = self._whois_servers_conn[0]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        for server in self._whois_servers_conn:
            server.close()
        return False

    def get_whois_info(self, address) -> WhoisInfo:
        result_info = self._server.get_whois_info(address=address)
        if not (result_info is None):
            return result_info

        for server in self._whois_servers_conn:
            if server is self._server:
                continue
            result_info = server.get_whois_info(address=address)
            if not(result_info is None):
                self._server = server
                return result_info
        return WhoisInfo(source='',
                         ip=address,
                         as_num='',
                         country_code='',
                         net='',
                         isp='')


def main():
    db = WhoisDB()
    info = db.get_whois_info('152.255.176.82')
    # 88.152.112.110 ripe
    # 197.159.12.128 AFRINIC
    # 104.152.112.110 arin
    # 177.25.112.110 lacnic
    # 110.152.110.32 apnic
    print()


if __name__ == '__main__':
    main()
