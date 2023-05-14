import pickle
from pathlib import Path
from typing import Iterable

from entities import *



class Cache:
    def __init__(self, filename):
        self._file = Path(filename)
        self._cache = dict()
        self._load_cache()

    def _load_cache(self):
        if self._file.exists():
            with open(self._file.name, 'rb') as f:
                try:
                    self._cache = pickle.load(f)
                except EOFError:
                    print(f'File \'{self._file.name}\' is empty.')
                else:
                    print(f'Cache \'{self._file.name}\' was loaded.')
                    self.validate_cache()
        else:
            print(f'File \'{self._file.name}\' is not exist.')

    def dump_cache(self):
        self.validate_cache()
        with open(self._file.name, 'wb') as f:
            pickle.dump(self._cache, f)
        print(f'Cache was dumped into \'{self._file.name}\'.')

    def __getitem__(self, item: DNSQuestion) -> list[DNSRecord]:
        records = list()
        if item in self._cache:
            for record in self._cache[item]:
                if not record.is_expire():
                    records.append(record)
            if len(records) > 0:
                self._cache[item] = records
            else:
                del self._cache[item]
        return records

    def __setitem__(self, key: DNSQuestion, value: DNSRecord):
        if not value.is_expire():
            if key not in self._cache:
                self._cache[key] = [value]
            else:
                self._cache[key].append(value)

    def __contains__(self, item):
        return len(self[item]) > 0

    def update(self, records: Iterable[DNSRecord]):
        for record in records:
            self[record.extract_query()] = record

    def validate_cache(self):
        for key in self._cache.keys():
            self._cache[key]