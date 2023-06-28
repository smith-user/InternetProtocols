from typing import Dict, List
import hashlib
import time


class ContentMessage:
    _headers: Dict[str, str]
    _body: bytes

    def __init__(self, headers: Dict[str, str], body: bytes):
        self._headers = headers
        self._body = body

    def __bytes__(self):
        return b'\r\n'.join([
            *(f'{key}: {value}'.encode() for key, value in self._headers.items()),
            b'',
            self._body
        ])


class Message:
    _headers: Dict[str, str]
    _body: List[ContentMessage]

    def __init__(self, headers: Dict[str, str], body: List[ContentMessage], boundary: str):
        self._headers = headers
        self._body = body
        self._boundary = boundary

    def __bytes__(self):
        head = '\r\n'.join([
            *(f'{key}: {value}' for key, value in self._headers.items()),
            '', ''
        ])
        body = f'--{self._boundary}\r\n'.encode().join([
            b'',
            *(content.__bytes__() + b'\r\n' for content in self._body)
        ]) + f'\r\n--{self._boundary}--\r\n'.encode()
        return head.encode() + body + b'\r\n.\r\n'

