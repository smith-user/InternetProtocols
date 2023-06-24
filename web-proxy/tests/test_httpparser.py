import unittest
from unittest import IsolatedAsyncioTestCase

from parameterized import parameterized

from proxy.httpparser import *
from proxy.httpparser import _parse_headers, \
    _read_chunked_content, _read_first_line_and_headers


class ParserTests(unittest.TestCase):
    def test_parse_header(self):
        data = b'host: www.example.ru:8080\r\n' \
               b'accept-language: ru-ru\r\n' \
               b'connection: Keep-Alive\r\n' \
               b'content-type: text/html\r\n' \
               b'content-length: 182\r\n\r\n'
        actual = _parse_headers(data)
        self.assertDictEqual({
            'host': 'www.example.ru:8080',
            'accept-language': 'ru-ru',
            'connection': 'Keep-Alive',
            'content-type': 'text/html',
            'content-length': '182'
        }, actual)

    def test_http_property_getters(self):
        httpproperty = HTTPProperty()
        self.assertEqual(None, httpproperty.type)
        self.assertEqual(0, httpproperty.length)
        httpproperty.headers = {'content-type': 'text/html',
                                'content-length': '80'}
        self.assertEqual('text/html', httpproperty.type)
        self.assertEqual('80', httpproperty.length)

    def test_del_proxy_headers(self):
        httprequest = HTTPRequest()
        httprequest.headers = {
            'accept-language': 'en-us',
            'proxy-connection': 'keep-alive',
            'connection': 'keep-alive',
            'proxy-authorization': 'Basic QWxhZGRpbjpvcGVuIHNlc2FtZQ=='
        }
        httprequest.del_proxy_head()
        self.assertDictEqual({
            'accept-language': 'en-us',
            'connection': 'keep-alive'
        }, httprequest.headers)

    @parameterized.expand([
        ['br', b'\x8b\x01\x80test\x03'],
        ['unknown', b'test']
    ])
    def test_compress_content(self, encoding: str, expected: bytes):
        httpproperty = HTTPProperty()
        httpproperty.headers['content-encoding'] = encoding
        httpproperty.content = b'test'
        self.assertEqual(expected, httpproperty._compress_content())

    @parameterized.expand([
        ['gzip', b'test', b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x03+I-'
                          b'.\x01\x00\x0c~\x7f\xd8\x04\x00\x00\x00'],
        ['br', b'test', b'\x8b\x01\x80test\x03'],
        ['unknown', b'test', b'test']
    ])
    def test_decompress_content(self, encoding: str,
                                expected: bytes, content: bytes):
        httpproperty = HTTPProperty()
        httpproperty.headers['content-encoding'] = encoding
        httpproperty.content = content
        httpproperty._decompress_content()
        self.assertEqual(expected, httpproperty.content)

    @parameterized.expand([
        [
            # name
            'without_encoding',
            # proto code message
            'HTTP/1.1', 200, 'OK',
            # headers
            {'content-length': '4'},
            # content
            b'test',
            # expected
            b'HTTP/1.1 200 OK\r\n'
            b'content-length: 4\r\n'
            b'\r\n'
            b'test'
        ],
        [
            # name
            'with_encoding',
            # proto code message
            'HTTP/1.1', 200, 'OK',
            # headers
            {'content-encoding': 'br'},
            # content
            b'test',
            # expected
            b'HTTP/1.1 200 OK\r\n'
            b'content-encoding: br\r\n'
            b'\r\n'
            b'\x8b\x01\x80test\x03'
        ]
    ])
    def test_http_response_to_bytes(
            self, _: str,
            proto: str, code: int, message: str,
            headers: dict[str, str], content: bytes, expected: bytes):
        httpresponse = HTTPResponse()
        httpresponse.proto = proto
        httpresponse.code = code
        httpresponse.message = message
        httpresponse.headers = headers
        httpresponse.content = content
        self.assertEqual(expected, bytes(httpresponse))

    @parameterized.expand([
        [
            # name
            'without_encoding',
            # method path proto
            'POST', '/test.php', 'HTTP/1.1',
            # headers
            {'host': 'example:8080'},
            # content
            b'test',
            # expected
            b'POST /test.php HTTP/1.1\r\n'
            b'host: example:8080\r\n'
            b'\r\n'
            b'test'
        ],
        [
            # name
            'with_encoding',
            # method path proto
            'POST', '/test.php', 'HTTP/1.1',
            # headers
            {'content-encoding': 'br'},
            # content
            b'test',
            # expected
            b'POST /test.php HTTP/1.1\r\n'
            b'content-encoding: br\r\n'
            b'\r\n'
            b'\x8b\x01\x80test\x03'
        ]
    ])
    def test_http_request_to_bytes(
            self, _: str,
            method: str, path: str, proto: str,
            headers: dict[str, str], content: bytes, expected: bytes):
        httrequest = HTTPRequest()
        httrequest.method = method
        httrequest.path = path
        httrequest.proto = proto
        httrequest.headers = headers
        httrequest.content = content
        self.assertEqual(expected, bytes(httrequest))


class ParserAsyncTests(IsolatedAsyncioTestCase):

    @staticmethod
    def get_reader(data: bytes) -> StreamReader:
        s = StreamReader()
        s.feed_data(data)
        s.feed_eof()
        return s

    async def test_read_chunked_content(self):
        s = self.get_reader(b'29\r\n'
                            b'<html><body><p>The file you requested is \r\n'
                            b'5\r\n'
                            b'3,400\r\n'
                            b'23\r\n'
                            b' bytes long and was last modified: \r\n'
                            b'1d\r\n'
                            b'Sat, 20 Mar 2004 21:12:00 GMT\r\n'
                            b'13\r\n'
                            b'.</p></body></html>\r\n'
                            b'0\r\n')
        actual = await _read_chunked_content(s)
        self.assertEqual(b'<html><body><p>The file you requested is'
                         b' 3,400 bytes long and was last modified: '
                         b'Sat, 20 Mar 2004 21:12:00 GMT.</p></body></html>',
                         actual)

    async def test_read_chunked_content_exc(self):
        s = self.get_reader(b'29\r\n'
                            b'<html><body><p>The file you requested is \r\n'
                            b'5\r\n'
                            b'3,400\r\n'
                            b'23\r\n'
                            b' bytes long')
        with self.assertRaises(HTTPParsingException):
            _ = await _read_chunked_content(s)

    @parameterized.expand([
        ['request', b'GET /test.php HTTP/1.1\r\n', b'GET /test.php HTTP/1.1'],
        ['response', b'HTTP/1.1 200 OK\r\n', b'HTTP/1.1 200 OK']
    ])
    async def test_read_first_line_and_headers(self, _: str,
                                               first_line: bytes,
                                               expected: bytes):
        reader = self.get_reader(
            first_line +
            b'host: www.example.ru:8080\r\n'
            b'accept-language: ru-ru\r\n\r\n')
        actual = await _read_first_line_and_headers(reader)
        self.assertEqual(actual, [expected,
                                  b'host: www.example.ru:8080\r\n'
                                  b'accept-language: ru-ru\r\n\r\n'
                                  ])

    async def test_read_first_line_and_headers_exc(self):
        reader = self.get_reader(
            b'GET /test.php HTTP/1.1\r\n'
            b'host: www.example.ru:8080\r\n')
        with self.assertRaises(HTTPParsingException):
            _ = await _read_first_line_and_headers(reader)

    @parameterized.expand([
        [
            # name
            'with_content_length',
            # package
            b'HTTP/1.1 200 OK\r\n'
            b'Content-Length: 39\r\n'
            b'Content-Type: text/html\r\n'
            b'\r\n'
            b'<html><body><h1>YES!</h1></body></html>',
            # proto code message
            'HTTP/1.1', 200, 'OK',
            # headers
            {'content-length': '39', 'content-type': 'text/html'},
            # content
            b'<html><body><h1>YES!</h1></body></html>'
        ],
        [
            # name
            'chunked_content',
            # package
            b'HTTP/1.1 200 OK\r\n'
            b'Transfer-Encoding: chunked\r\n'
            b'Connection: keep-alive\r\n'
            b'\r\n'
            b'8\r\n'
            b'Chunked \r\n'
            b'7\r\n'
            b'content\r\n'
            b'0\r\n',
            # proto code message
            'HTTP/1.1', 200, 'OK',
            # headers
            {'content-length': '15', 'connection': 'keep-alive'},
            # content
            b'Chunked content'
        ],
        [
            # name
            'chunked_content_with_trailer',
            # package
            b'HTTP/1.1 200 OK\r\n'
            b'Transfer-Encoding: chunked\r\n'
            b'Connection: keep-alive\r\n'
            b'Trailer: Expires\r\n'
            b'\r\n'
            b'8\r\n'
            b'Chunked \r\n'
            b'7\r\n'
            b'content\r\n'
            b'0\r\n'
            b'Expires: Sat, 27 Mar 2004 21:12:00 GMT\r\n',
            # proto code message
            'HTTP/1.1', 200, 'OK',
            # headers
            {'content-length': '15', 'connection': 'keep-alive',
             'expires': 'Sat, 27 Mar 2004 21:12:00 GMT'},
            # content
            b'Chunked content'
        ]
    ])
    async def test_http_response_parse(
            self, _: str, package: bytes,
            proto: str, code: int, message: str,
            headers: dict[str, str], content: bytes):
        reader = self.get_reader(package)
        httpresponse = await HTTPResponse().from_stream(reader)
        self.assertEqual(proto, httpresponse.proto)
        self.assertEqual(code, httpresponse.code)
        self.assertEqual(message, httpresponse.message)
        self.assertDictEqual(headers, httpresponse.headers)
        self.assertEqual(content, httpresponse.content)

    @parameterized.expand([
        [
            # name
            'with_port',
            # package
            b'POST /example HTTP/1.1\r\n'
            b'Host: example.com:8888\r\n'
            b'Content-Length: 4\r\n'
            b'\r\n'
            b'test',
            # proto code message
            'POST', 'example.com', 8888, 'HTTP/1.1',
            # headers
            {'host': 'example.com:8888', 'content-length': '4'},
            # content
            b'test'
        ],
        [
            # name
            'without_port',
            # package
            b'POST /example HTTP/1.1\r\n'
            b'Host: example.com\r\n'
            b'Content-Length: 4\r\n'
            b'\r\n'
            b'test',
            # proto code message
            'POST', 'example.com', 80, 'HTTP/1.1',
            # headers
            {'host': 'example.com', 'content-length': '4'},
            # content
            b'test'
        ]
    ])
    async def test_http_request_parse(
            self, _: str, package: bytes,
            method: str, host: str, port: int, proto: str,
            headers: dict[str, str], content: bytes):
        reader = self.get_reader(package)
        httprequst = await HTTPRequest().from_stream(reader)
        self.assertEqual(method, httprequst.method)
        self.assertEqual(host, httprequst.host)
        self.assertEqual(port, httprequst.port)
        self.assertEqual(proto, httprequst.proto)
        self.assertDictEqual(headers, httprequst.headers)
        self.assertEqual(content, httprequst.content)
