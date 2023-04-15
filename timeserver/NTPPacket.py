import datetime
import struct
import time

MODE_CLIENT = 3
MODE_SERVER = 4
NTP_v1 = 1
NTP_v2 = 2
NTP_v3 = 3
NTP_v4 = 4

FORMAT_DIFF = (datetime.date(1970, 1, 1) - datetime.date(1900, 1, 1)).days * 24 * 3600


def get_fraction(number, precision):
    return int((number - int(number)) * 2 ** precision)


class NTPPacket:
    _FORMAT = "!B B b b 11I"

    def __init__(self,
                 leap_indicator=0,
                 version=NTP_v3,
                 mode=MODE_CLIENT,
                 stratum=0,
                 pool=0,
                 precision=0,
                 root_delay=0,
                 root_dispersion=0,
                 ref_id=0,
                 reference=0,
                 originate=0,
                 receive=0,
                 transmit=time.time() + FORMAT_DIFF):
        self.leap_indicator = leap_indicator
        self.version = version
        self.mode = mode
        self.stratum = stratum
        self.pool = pool
        self.precision = precision
        self.root_delay = root_delay
        self.root_dispersion = root_dispersion
        self.ref_id = ref_id
        self.reference = reference
        self.originate = originate
        self.receive = receive
        self.transmit = transmit

    def pack(self):
        return struct.pack(NTPPacket._FORMAT,
                           (self.leap_indicator << 6) +
                           (self.version << 3) + self.mode,
                           self.stratum,
                           self.pool,
                           self.precision,
                           int(self.root_delay) + get_fraction(self.root_delay, 16),
                           int(self.root_dispersion) +
                           get_fraction(self.root_dispersion, 16),
                           self.ref_id,
                           int(self.reference),
                           get_fraction(self.reference, 32),
                           int(self.originate),
                           get_fraction(self.originate, 32),
                           int(self.receive),
                           get_fraction(self.receive, 32),
                           int(self.transmit),
                           get_fraction(self.transmit, 32))

    def unpack(self, data: bytes):
        unpacked_data = struct.unpack(NTPPacket._FORMAT, data)

        self.leap_indicator = unpacked_data[0] >> 6  # 2 bits
        self.version = unpacked_data[0] >> 3 & 0b111  # 3 bits
        self.mode = unpacked_data[0] & 0b111  # 3 bits

        self.stratum = unpacked_data[1]  # 1 byte
        self.pool = unpacked_data[2]  # 1 byte
        self.precision = unpacked_data[3]  # 1 byte

        # 2 bytes | 2 bytes
        self.root_delay = (unpacked_data[4] >> 16) + \
                          (unpacked_data[4] & 0xFFFF) / 2 ** 16
        # 2 bytes | 2 bytes
        self.root_dispersion = (unpacked_data[5] >> 16) + \
                               (unpacked_data[5] & 0xFFFF) / 2 ** 16

        # 4 bytes
        self.ref_id = str((unpacked_data[6] >> 24) & 0xFF) + "." + \
                      str((unpacked_data[6] >> 16) & 0xFF) + "." + \
                      str((unpacked_data[6] >> 8) & 0xFF) + "." + \
                      str(unpacked_data[6] & 0xFF)

        self.reference = unpacked_data[7] + unpacked_data[8] / 2 ** 32  # 8 bytes
        self.originate = unpacked_data[9] + unpacked_data[10] / 2 ** 32  # 8 bytes
        self.receive = unpacked_data[11] + unpacked_data[12] / 2 ** 32  # 8 bytes
        self.transmit = unpacked_data[13] + unpacked_data[14] / 2 ** 32  # 8 bytes

        return self

    def to_display(self):
        return "Leap indicator: {0.leap_indicator}\n" \
               "Version number: {0.version_number}\n" \
               "Mode: {0.mode}\n" \
               "Stratum: {0.stratum}\n" \
               "Pool: {0.pool}\n" \
               "Precision: {0.precision}\n" \
               "Root delay: {0.root_delay}\n" \
               "Root dispersion: {0.root_dispersion}\n" \
               "Ref id: {0.ref_id}\n" \
               "Reference: {0.reference}\n" \
               "Originate: {0.originate}\n" \
               "Receive: {0.receive}\n" \
               "Transmit: {0.transmit}" \
            .format(self)

    def get_time_different(self, arrive_time):
        return (self.receive - self.originate - arrive_time + self.transmit) / 2
