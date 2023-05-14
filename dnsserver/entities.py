import struct
import time
from itertools import chain

TYPE_A = 1
TYPE_AAAA = 28
TYPE_NS = 2
TYPE_PTR = 12
TYPE_SOA = 6


class DNSPackage:

    def __init__(self, data):
        self.id = 0
        self.flags = 0
        self.questions: list[DNSQuestion] = []
        self.answers: list[DNSRecord] = []
        self.authority: list[DNSRecord] = []
        self.additional: list[DNSRecord] = []
        self._parse_data(data)

    @property
    def qdcount(self):
        return len(self.questions)

    @property
    def ancount(self):
        return len(self.answers)

    @property
    def nscount(self):
        return len(self.authority)

    @property
    def arcount(self):
        return len(self.additional)

    def _parse_data(self, data):
        (
            self.id, self.flags,
            qdcount, ancount, nscount, arcount
        ) = struct.unpack_from('!HHHHHH', data, 0)
        offset = 12
        for i in range(qdcount):
            query, offset = DNSQuestion.parse_question(data, offset)
            self.questions.append(query)
        for i in range(ancount):
            record, offset = DNSRecord.parse_record(data, offset)
            self.answers.append(record)
        for i in range(nscount):
            record, offset = DNSRecord.parse_record(data, offset)
            self.authority.append(record)
        for i in range(arcount):
            record, offset = DNSRecord.parse_record(data, offset)
            self.additional.append(record)

    @property
    def records(self) -> iter:
        return iter(chain(self.answers, self.authority, self.additional))

    def __bytes__(self):
        result_bytes = struct.pack('!HHHHHH',
                                   self.id,
                                   self.flags,
                                   self.qdcount,
                                   self.ancount,
                                   self.nscount,
                                   self.arcount
                                   )
        for entity in chain(self.questions,
                            self.answers,
                            self.authority,
                            self.additional):
            result_bytes += bytes(entity)
        return result_bytes

    def __str__(self):
        data = dict()
        for key, value in self.__dict__.items():
            if type(value) is list:
                data[key] = [str(elem) for elem in value]
            else:
                data[key] = str(value)
        return str(data)


class DNSQuestion:
    def __init__(self, qname=None, qtype=None, qclass=None):
        self.qname = qname
        self.qtype = qtype
        self.qclass = qclass

    @staticmethod
    def parse_question(data: bytes, offset):
        question = DNSQuestion()
        question.qname, offset = read_name(data, offset)
        question.qtype = read_short(data, offset)
        offset += 2
        question.qclass = read_short(data, offset)
        offset += 2
        return question, offset

    def __bytes__(self):
        return name_to_bytes(self.qname) + struct.pack('!HH', self.qtype, self.qclass)

    def __hash__(self):
        return hash(f'{self.qname} {self.qtype} {self.qclass}')

    def __eq__(self, y):
        return all((self.qname == y.qname,
                    self.qtype == y.qtype,
                    self.qclass == y.qclass))

    def __str__(self):
        return str(self.__dict__)


class DNSRecord:

    def __init__(self, name=None, type=None, class_rr=None,
                 ttl=None, rdata=None, exp_time=None):
        self.name = name
        self.type = type
        self.class_rr = class_rr
        self.rdata = rdata
        self.ttl = ttl
        if exp_time:
            self.exp_time = exp_time
        else:
            self.exp_time = int(time.time()) + self.ttl if self.ttl else None

    @staticmethod
    def parse_record(data: bytes, offset):
        question, offset = DNSQuestion.parse_question(data, offset)
        record = DNSRecord()
        record.name = question.qname
        record.type = question.qtype
        record.class_rr = question.qclass
        record.ttl = struct.unpack_from('!I', data, offset)[0]
        offset += 4
        record.exp_time = int(time.time()) + record.ttl
        rdlength = read_short(data, offset)
        offset += 2
        if record.type == TYPE_NS:
            record.rdata = name_to_bytes(read_name(data, offset)[0])
        else:
            record.rdata = data[offset:offset + rdlength]
        return record, offset + rdlength

    def __bytes__(self):
        packed = struct.pack('!HHIH', self.type, self.class_rr, self.ttl, len(self.rdata))
        return name_to_bytes(self.name) + packed + self.rdata

    def extract_query(self) -> DNSQuestion:
        return DNSQuestion(qname=self.name,
                           qtype=self.type,
                           qclass=self.class_rr)

    def is_expire(self):
        return self.exp_time <= int(time.time())

    def __str__(self):
        return str(self.__dict__)


def read_short(data: bytes, offset):
    return struct.unpack_from('!H', data, offset)[0]


def read_name(data: bytes, offset) -> (str, int):
    labels = list()
    while data[offset] != 0 and data[offset] < 0x80:
        octet_number = data[offset]
        labels.append(data[offset + 1:offset + octet_number + 1].decode('utf-8'))
        offset += octet_number + 1
    if data[offset] == 0 and len(labels) == 0:
        name = '.'
    elif len(labels) > 0:
        name = '.'.join(labels)
    else:
        name = ''
    if data[offset] >= 0x80:
        # Message compression
        pointer = read_short(data, offset) & 0x3fff  # 1fff
        offset += 2
        end_name, _ = read_name(data, pointer)
        name = f'{name}.{end_name}' if len(name) > 0 else end_name
    else:
        offset += 1
    return name, offset


def name_to_bytes(name):
    buffer: bytes = b''
    for label in name.split('.'):
        buffer += struct.pack('B', len(label))
        buffer += label.encode(encoding='utf-8')
    return buffer + b'\0'
