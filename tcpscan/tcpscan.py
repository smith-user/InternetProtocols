#! /usr/bin/python
import socket
from argparse import ArgumentParser

parser = ArgumentParser(description='TCP сканнер')
parser.add_argument('--addr', type=str, help='ip или доменное имя', default='127.0.0.1')
parser.add_argument('--min', type=int, help='нижняя граница диапазона портов', default=1)
parser.add_argument('--max', type=int, help='верхняя граница диапазона портов', default=65535)

args = parser.parse_args().__dict__
addr = socket.gethostbyname(args['addr'])
ports_range = (args['min'], args['max'])
print(f'Доступные порты {addr}.')
for port in range(ports_range[0], ports_range[1]):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(5)
        if s.connect_ex((addr, port)) == 0:
            print(f'{port}'.rjust(6))
