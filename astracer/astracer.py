#! /usr/bin/python
import itertools
import socket
from argparse import ArgumentParser
import subprocess
import re

from whois import WhoisDB
from whois import WhoisInfo
from itertools import zip_longest

PRIVATE_IP = {
    ((10, 0, 0, 0), (10, 255, 255, 255)),
    ((172, 16, 0, 0), (172, 31, 255, 255)),
    ((192, 168, 0, 0), (192, 168, 255, 255)),
    ((127, 0, 0, 0), (127, 255, 255, 255))
}


def v(x):
    return '---' if x == None or len(str(x)) == 0 else x


def is_local_ip(address: str) -> bool:
    splited = tuple(map(int, address.split('.')))
    for l_addr, r_addr in PRIVATE_IP:
        if l_addr <= splited <= r_addr:
            return True
    return False


def main(args):
    if args.ipaddr:
        addr = args.ipaddr
        print(f'traceroute to {addr}')
    else:
        addr = socket.gethostbyname(args.domain)
        print(f'traceroute to {args.domain} ({addr})')
    traceroute = f'traceroute --max-hops=40 --queries=1 {addr}'
    traceroute_res = subprocess.check_output(traceroute, shell=True).decode('utf-8')
    print(traceroute_res)
    print()
    print()

    ip_regex = re.compile(r'^ *(\d+) .+?\((\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3})\)', re.MULTILINE)
    ips = ip_regex.findall(traceroute_res)
    # ips.remove(ips[0])

    table_str = '{:<3}|{:<18}|{:<32}|{:<8}|{:<10}|{:<7}|{:<50}'
    print(table_str.format('№', 'IP', 'Network', 'AS', 'Country', 'Source', 'ISP (ORG)'))
    with WhoisDB() as whois_db:
        for idx, ip in ips:
            if is_local_ip(ip):
                info = WhoisInfo(ip=ip, net=None, as_num=None,
                                 country_code=None, source=None, isp=None)
            else:
                info = whois_db.get_whois_info(ip)
            print(table_str.format(
                idx, v(info.ip), v(info.net), v(info.as_num),
                v(info.country_code), v(info.source).upper(), v(info.isp)))


if __name__ == '__main__':
    parser = ArgumentParser(
        description='Трассировка автономных систем. '
                    'Пользователь вводит доменное имя или IP адрес. '
                    'Осуществляется трассировка до указанного узла и'
                    'определяется к какой автономной системе, стране'
                    ' и провайдеру относится каждый из полученных'
                    ' IP адресов маршрутизаторов.')
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-i", "--ipaddr", type=str, help='ip-адрес')
    group.add_argument("-d", "--domain", type=str, help='доменное имя')
    args = parser.parse_args()
    main(args)
