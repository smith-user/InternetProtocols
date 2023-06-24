import zlib
from abc import ABC
from asyncio import StreamReader
from dataclasses import dataclass, field
from typing import Dict, Optional
from asyncio.exceptions import IncompleteReadError
import brotli

from proxy.errors import HTTPParsingException


CRLF = b'\r\n'


def _parse_headers(data: bytes) -> dict[str, str]:
    lines = data.split(b'\r\n')
    headers = dict()
    for line in filter(lambda x: b': ' in x, lines):
        name, value = line.split(b': ', maxsplit=1)
        headers.update(
            {str.lower(name.decode()): value.decode()}
        )
    return headers


async def _read_chunked_content(source: StreamReader) -> bytes:
    content = b''
    try:
        count = int(await source.readuntil(CRLF), 16)
        while count != 0:
            content += await source.readexactly(count)
            await source.readuntil(CRLF)
            count = int(await source.readuntil(CRLF), 16)
        return content
    except IncompleteReadError as e:
        raise HTTPParsingException(e) from e


async def _read_first_line_and_headers(source: StreamReader) -> (bytes, bytes):
    try:
        headers_bytes = await source.readuntil(CRLF * 2)
    except IncompleteReadError as e:
        raise HTTPParsingException(e) from e
    return headers_bytes.split(CRLF, maxsplit=1)


@dataclass
class HTTPProperty(ABC):
    headers: Dict[str, str] = field(default_factory=dict)

    @property
    def type(self) -> Optional[str]:
        return self.headers.get('content-type', None)

    @property
    def length(self) -> Optional[str]:
        return self.headers.get('content-length', 0)

    @length.setter
    def length(self, value: int):
        self.headers['content-length'] = str(value)

    async def _read_content(self, source: StreamReader):
        if 'transfer-encoding' in self.headers:
            self.content = await _read_chunked_content(source)
            if 'trailer' in self.headers:
                foot_headers_count = len(self.headers['trailer'].split(','))
                foot = b''
                for i in range(foot_headers_count):
                    foot += await source.readuntil(CRLF)
                self.headers.update(_parse_headers(foot))
                del self.headers['trailer']
            self.headers['content-length'] = f'{len(self.content)}'
            del self.headers['transfer-encoding']
        else:
            if 'content-length' in self.headers:
                self.content = await source.readexactly(int(self.length))
        self._decompress_content()

    def _decompress_content(self):
        if 'content-encoding' in self.headers:
            encode = self.headers['content-encoding']
            if 'gzip' == encode:
                self.content = zlib.decompress(self.content,
                                               16 + zlib.MAX_WBITS)
            elif 'br' == encode:
                self.content = brotli.decompress(self.content)

    def _compress_content(self) -> bytes:
        if 'content-encoding' in self.headers:
            encode = self.headers['content-encoding']
            if 'gzip' == encode:
                return zlib.compress(self.content, wbits=16+zlib.MAX_WBITS)
            elif 'br' == encode:
                return brotli.compress(self.content)
        return self.content

    def _to_bytes(self, first: str, second: str, third: str) -> bytes:
        if not all((first, second, third)):
            return b''
        bytes_list = [
            f'{first} {second} {third}'.strip().encode(),
            *(
                f'{name}: {value}'.encode()
                for name, value in self.headers.items()
            ),
            b'',
            self._compress_content()
        ]
        return b'\r\n'.join(bytes_list)


@dataclass
class HTTPRequest(HTTPProperty):
    method: str = None
    path: str = None
    proto: str = None
    host: str = None
    port: int = None
    headers: Dict[str, str] = field(default_factory=dict)
    content: bytes = field(default_factory=(lambda: b''))

    async def from_stream(self, source: StreamReader) -> 'HTTPRequest':
        line, headers_bytes = await _read_first_line_and_headers(source)
        (self.method,
         self.path,
         self.proto) = [data.decode() for data in line.split(b' ', maxsplit=2)]
        self.headers = _parse_headers(headers_bytes)
        self._extract_host_port()

        await self._read_content(source)
        return self

    def _extract_host_port(self):
        connection_inf = self.headers.get('host', None)
        if connection_inf:
            if connection_inf.count(':'):
                self.host, port = connection_inf.split(':')
            else:
                self.host, port = connection_inf, 80
            self.port = int(port)

    def del_proxy_head(self) -> None:
        headers = ['proxy-connection', 'proxy-authorization']
        for header in headers:
            if header in self.headers.keys():
                del self.headers[header]

    def __bytes__(self) -> bytes:
        return self._to_bytes(self.method, self.path, self.proto)


@dataclass
class HTTPResponse(HTTPProperty):
    proto: str = None
    code: int = None
    message: str = None
    headers: Dict[str, str] = field(default_factory=dict)
    content: bytes = field(default_factory=(lambda: b''))

    async def from_stream(self, source: StreamReader) -> 'HTTPResponse':
        line, headers_bytes = await _read_first_line_and_headers(source)
        (self.proto,
         code,
         self.message) = [v.decode() for v in line.split(b' ', maxsplit=2)]
        self.code = int(code)
        self.headers = _parse_headers(headers_bytes)
        await self._read_content(source)
        return self

    def __bytes__(self) -> bytes:
        return self._to_bytes(self.proto, str(self.code), self.message)


HTTPCode200 = HTTPResponse(
    proto='HTTP/1.1',
    code=200,
    message='Connection established'
)
HTTPCode502 = HTTPResponse(
    proto='HTTP/1.1',
    code=502,
    message='Bad Gateway'
)
