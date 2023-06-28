import argparse
import hashlib
import logging
import socket
import ssl
import time
from dataclasses import dataclass
from typing import Optional, Tuple, List
import base64
import configparser

from message import ContentMessage, Message


@dataclass
class SenderException(Exception):
    message: str


@dataclass
class ConfigReadingException(SenderException):
    message: str


class SMTPSender:
    _MIME_TYPES = {
        'png': 'image/png',
        'jpg': 'image/jpg',
        'html': 'text/html',
        'txt': 'text/html',
        'pdf': 'application/pdf'
    }
    _logger = logging.getLogger('SMTPSender')

    def __init__(self, config: str):
        self._sock: socket.socket = socket.socket()
        self._boundary: str = self._get_boundary()
        self._read_config(config)

    def _read_config(self, filename: str):
        config = configparser.ConfigParser()
        config.read(filename)

        cnfg_settings = config['Settings']
        self._server: str = cnfg_settings['server']
        self._port: int = cnfg_settings.getint('port', fallback=None) or 25
        self._tls: bool = cnfg_settings.getboolean('tls')

        cnfg_auth = config['Auth']
        self._login: str = cnfg_auth['login']
        self._password: str = cnfg_auth['password']

        cnfg_message = config['Message']
        self._from: str = cnfg_message['from']
        self._subject: str = cnfg_message['subject'].replace('\n', ' ')
        self._message_filepath: str = cnfg_message['message_filepath']

        self._recipients: list[str] = [value for _, value in config.items('Recipients')]
        self._attachments: list[str] = [value for _, value in config.items('Attachments')]
        self._logger.info(f'Config file {filename} was read successfully.')

    def _recv_message(self) -> Optional[bytes]:
        buffer = []
        try:
            while True:
                message = self._sock.recv(1024)
                if not message:
                    break
                buffer.append(message)
        except socket.timeout:
            pass
        return b''.join(buffer)

    @staticmethod
    def _get_boundary():
        hashlib.sha256().update(str(time.time()).encode("utf-8"))
        return f'bound.{hashlib.sha256().hexdigest()[:16]}.smtp.client'

    def _open_content(self) -> List[ContentMessage]:
        result: List[ContentMessage] = []
        with open(self._message_filepath, 'rb') as message_file:
            ext = self._message_filepath.rsplit('.', maxsplit=1)[1]
            result.append(ContentMessage(
                headers={'Content-Type': f'{self._MIME_TYPES[ext]};charset=utf-8\r\n'},
                body=message_file.read(),
            ))
        for attachment in self._attachments:
            name = attachment.rsplit('/', maxsplit=1)[1]
            ext = name.rsplit('.', maxsplit=1)[1]
            with open(attachment, 'rb') as file:
                result.append(ContentMessage(
                    headers={'Content-type': f'{self._MIME_TYPES[ext]};\r\n\tname={name}',
                             'Content-transfer-encoding': 'base64',
                             'Content-disposition': f'attachment;\r\n\tfilename:"{name}"'},
                    body=base64.b64encode(file.read()),
                ))
        return result

    def _create_message(self) -> Message:
        return Message(
            headers={
                'From': f'<{self._from}>',
                'To': ',\r\n\t'.join([f'<{rcpt}>' for rcpt in self._recipients]),
                'Subject': self._get_subject(),
                'Content-type': f'multipart/mixed; boundary={self._boundary}'
            },
            body=self._open_content(),
            boundary=self._boundary
        )

    def _get_subject(self) -> str:
        result = []
        count = 32
        for i in range(len(self._subject) // count + 1):
            start = i * count
            end = (i + 1) * count
            part = base64.b64encode(self._subject[start:end].encode())
            result.append(f'=?utf-8?B?{part.decode()}?=')
        return '\r\n\t'.join(result)

    @staticmethod
    def _ensure_code_correct(accept: bytes, accept_code: bytes) -> None:
        accept = accept.strip(b'\r\n').split(b'\r\n')[-1]
        if not accept.startswith(accept_code):
            raise SenderException(accept.decode())

    def _send(self, commands: List[Tuple[bytes, bytes]], verbose=True) -> list[str]:
        result = []
        for command, code in commands:
            self._sock.sendall(command)
            answer = self._recv_message()
            result.append(answer.decode())
            self._ensure_code_correct(answer, code)
            if verbose:
                self._logger.info('(Client) ' + command.replace(b'\r\n', b'').decode())
            else:
                self._logger.info('(Client) ***hidden***')
            self._logger.info('(Server) ' + b'\n\t'.join(filter(None, answer.split(b'\r\n'))).decode())
        return result

    def send_message(self):
        self._sock = socket.socket()
        self._sock.settimeout(1)
        tls = False
        if self._port == 465:
            self._sock, tls = ssl.wrap_socket(self._sock), True
        try:
            self._sock.connect((self._server, self._port))
            self._ensure_code_correct(self._recv_message(), b'220')
            self._send([(f'EHLO {self._from}\r\n'.encode(), b'250')])
            if self._tls and not tls:
                self._send([(b'STARTTLS\r\n', b'220')])
                self._sock = ssl.wrap_socket(self._sock)
            self._send([(b'AUTH LOGIN\r\n', b'334')])
            self._send([
                (base64.b64encode(self._login.encode()) + b'\r\n', b'334'),
                (base64.b64encode(self._password.encode()) + b'\r\n', b'235')],
                verbose=False)
            self._send([(f'MAIL FROM: <{self._from}>\r\n'.encode(), b'250')])
            self._send([(f'RCPT TO: <{rcpt}>\r\n'.encode(), b'250') for rcpt in self._recipients])
            self._send([(b'DATA\r\n', b'354')])
            self._send([(self._create_message().__bytes__(), b'250')], verbose=False)
            self._send([(b'QUIT\r\n', b'221')])
            self._logger.info('Email was sent successfully.')
        finally:
            self._sock.close()


def main():
    parser = argparse.ArgumentParser(prog='SMTP-Client', description='SMTP-Client with config.')
    parser.add_argument('-i', '--ini', type=str, help='config filepath.')
    args = parser.parse_args()
    logger = logging.getLogger('main')

    logging.basicConfig(format='%(levelname)s - %(name)s - '
                               '%(asctime)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        level=logging.INFO)
    try:
        sender = SMTPSender(args.ini)
        sender.send_message()
    except SenderException as exc:
        logger.error(exc.message.strip('\r\n') or 'Unknown error!')
        exit(1)


if __name__ == '__main__':
    main()
