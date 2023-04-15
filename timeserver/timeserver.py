import configparser
import datetime
import socket
import sys
import time
from argparse import ArgumentParser

from NTPPacket import *
from NTPServer import NTPServer


class SectionError(Exception):
    pass


class PropertyError(Exception):
    pass


section_key = 'server'
property_key = 'sec'


def run_server(sec: int):
    server = NTPServer(host='127.0.0.1', port=123, sec=sec, users=10)
    server.run()


def main(filename: str):
    config = configparser.ConfigParser()
    if filename not in config.read(filename):
        raise FileNotFoundError
    sec = int(config[section_key][property_key])
    run_server(sec)


if __name__ == '__main__':
    parser = ArgumentParser(description='ОПИСАНИЕ')  # TODO
    parser.add_argument(
        "-f", "--file", type=str, default='config.ini', help='config file')
    args = parser.parse_args()
    try:
        main(args.file)
    except FileNotFoundError:
        print(f'Файл {args.file} не найден.')
        exit(1)

