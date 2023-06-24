import os
from pathlib import Path
from typing import Optional

from proxy.errors import ProxyError


def listdir(path: str) -> list[str]:
    return [os.path.join(path, filename) for filename in os.listdir(path)]


def save_file_at_dir(dir_path, filename, file_content, mode='wb'):
    os.makedirs(dir_path, exist_ok=True)
    with open(os.path.join(dir_path, filename), mode) as f:
        f.write(file_content)


class FileManager:
    _file: str = None

    def __init__(self, file: str,
                 dirname: Optional[str] = None,
                 check: bool = True):
        if dirname:
            self._file = os.path.join(dirname, file)
        else:
            self._file = file
        if check:
            self.check_exist()

    def check_exist(self):
        """
        :return:
        :raise FileNotExist
        """
        if not Path(self._file).exists():
            raise FileNotExist(f'File: {self._file} not exist!')

    def read_file(self) -> bytes:
        self.check_exist()
        with open(self._file, mode='rb') as f:
            return f.read()

    @property
    def filename(self):
        return self._file


class FileNotExist(ProxyError):
    def __init__(self, message):
        self.message = message
        super().__init__(message)
