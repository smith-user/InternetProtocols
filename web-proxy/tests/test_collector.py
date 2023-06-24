import json
import unittest
from unittest.mock import patch, MagicMock

from parameterized import parameterized

from common import FileManager
from features.collector import UserData, PasswordCollector
from proxy.httpparser import HTTPRequest


class UserDataTests(unittest.TestCase):
    def test_init(self):
        userdata = UserData(data={'key1': 'value1'},
                            host='example', client='localhost')
        expected = {'key1': 'value1', 'host': 'example', 'client': 'localhost'}
        self.assertDictEqual(expected, userdata.data)
        self.assertDictEqual(expected, userdata.to_dict())

        new_user = UserData(data={}).from_dict(expected)
        self.assertDictEqual(expected, new_user.to_dict())

    @parameterized.expand([
        ['equal', True,
         UserData({'key1': 'value1'}, host='host1', client='localhost:1234'),
         UserData({'key1': 'value1'}, host='host1', client='localhost:1234')
         ],
        ['different_data', False,
         UserData({'key1': 'value1'}, host='host1', client='localhost:1234'),
         UserData({}, host='host1', client='localhost:1234')
         ],
        ['different_host', False,
         UserData({'key1': 'value1'}, host='host1', client='localhost:1234'),
         UserData({'key1': 'value1'}, host='host2', client='localhost:1234')
         ],
        ['other_object', False,
         UserData({'key1': 'value1'}, host='host1', client='localhost:1234'),
         dict({'key1': 'value1', 'host': 'host1', 'client': 'localhost:1234'})
         ]
    ])
    def test_eq(self, name: str, expected: bool,
                userdata1: UserData, other):
        if expected:
            self.assertTrue(userdata1.__eq__(other))
            self.assertTrue(other.__eq__(userdata1))
        else:
            self.assertFalse(userdata1.__eq__(other))


class CollectorTests(unittest.TestCase):

    @staticmethod
    def get_request_with_url_form() -> HTTPRequest:
        request = HTTPRequest()
        request.method = 'POST'
        request.path = '/'
        request.proto = 'HTTP/1.1'
        request.headers = {'content-type': 'application/x-www-form-urlencoded',
                           'content-length': '13',
                           'host': 'example'}
        request.content = b'say=Hi&to=Mom'
        return request

    @staticmethod
    def get_request_with_auth_header():
        request = HTTPRequest()
        request.method = 'POST'
        request.path = '/'
        request.proto = 'HTTP/1.1'
        request.headers = {'authorization': 'Basic <credentials>',
                           'host': 'example'}
        return request

    @staticmethod
    def get_request_without_auth():
        request = HTTPRequest()
        request.method = 'GET'
        request.path = '/'
        request.proto = 'HTTP/1.1'
        request.headers = {'host': 'example'}
        return request

    @patch.object(PasswordCollector, 'dump')
    @patch.object(PasswordCollector, '_load')
    @patch.object(FileManager, 'check_exist')
    def test_init(self, mock_check, mock_load, mock_dump):
        collector = PasswordCollector(dirname='dirname', file='filename')
        self.assertEqual(set(), collector._users)
        self.assertEqual('dirname/filename', collector._file.filename)
        mock_check.assert_called()
        mock_load.assert_called()
        mock_dump.assert_called()

    @patch.object(PasswordCollector, 'dump')
    @patch.object(PasswordCollector, '_load')
    @patch.object(FileManager, 'check_exist')
    def test_init_decode_error(self, mock_check, mock_load, mock_dump):
        mock_load = MagicMock(side_effect=json.decoder.JSONDecodeError(
            msg='msg', doc='doc', pos=0))

        collector = PasswordCollector(dirname='dirname', file='filename')
        self.assertEqual(set(), collector._users)
        self.assertEqual('dirname/filename', collector._file.filename)
        mock_check.assert_called()
        mock_dump.assert_called()

    def test_url_form(self):
        userdata = PasswordCollector._url_form(
            client='localhost',
            request=self.get_request_with_url_form())
        self.assertDictEqual({'client': 'localhost',
                              'host': 'example',
                              'say': 'Hi',
                              'to': 'Mom'},
                             userdata.to_dict())

    @parameterized.expand([
        ['basic',
         'Basic YWxhZGRpbjpvcGVuc2VzYW1l',
         {'scheme': 'Basic', 'credential': 'aladdin:opensesame'}
         ],
        ['digest',
         'Digest username=<username>,realm=<realm>,uri=<url>,'
         'algorithm=<algorithm>,nonce=<nonce>,nc=<nc>,cnonce=<cnonce>,'
         'qop=<qop>,response=<response>,opaque=<opaque>',
         {'scheme': 'Digest', 'username': '<username>', 'realm': '<realm>',
          'uri': '<url>', 'algorithm': '<algorithm>', 'nonce': '<nonce>',
          'nc': '<nc>', 'cnonce': '<cnonce>', 'qop': '<qop>',
          'response': '<response>', 'opaque': '<opaque>'}
         ]
    ])
    def test_auth_header(self, name, value: str, expected: dict[str, str]):
        client = 'localhost'
        host = 'example'
        userdata = PasswordCollector._auth_header(
            client=client,
            host=host,
            value=value)
        expected['host'] = host
        expected['client'] = client
        self.assertDictEqual(expected,
                             userdata.to_dict())

    @patch.object(PasswordCollector, 'dump')
    @patch.object(PasswordCollector, '_load')
    @patch.object(FileManager, 'check_exist')
    def test_extract_userdata_url_form(self, mock_check, mock_load, mock_dump):
        collector = PasswordCollector(dirname='dirname', file='filename')

        userdata = UserData(data={}, client='test', host='test')
        request = self.get_request_with_url_form()

        with patch.object(PasswordCollector, '_url_form',
                          return_value=userdata) as mock_method:
            actual = collector._extract_userdata(
                client='test', data=request)
            self.assertEqual(userdata, actual)
        mock_method.assert_called_once_with(client='test', request=request)

    @patch.object(PasswordCollector, 'dump')
    @patch.object(PasswordCollector, '_load')
    @patch.object(FileManager, 'check_exist')
    def test_extract_userdata_auth_header(self, mock_check,
                                          mock_load, mock_dump):
        collector = PasswordCollector(dirname='dirname', file='filename')

        userdata = UserData(data={}, client='test', host='test')
        request = self.get_request_with_auth_header()

        with patch.object(PasswordCollector, '_auth_header',
                          return_value=userdata) as mock_method:
            actual = collector._extract_userdata(
                client='test', data=request)
            self.assertEqual(userdata, actual)
        mock_method.assert_called_once_with(
            client='test',
            value=request.headers['authorization'],
            host=request.headers['host'])

    @patch.object(PasswordCollector, 'dump')
    @patch.object(PasswordCollector, '_load')
    @patch.object(FileManager, 'check_exist')
    def test_extract_userdata_without_auth(self, mock_check,
                                           mock_load, mock_dump):
        collector = PasswordCollector(dirname='dirname', file='filename')

        actual = collector._extract_userdata(
            client='test', data=self.get_request_without_auth())
        self.assertEqual(None, actual)
