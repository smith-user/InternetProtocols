import socket

from NTPPacket import *


def main():
    # Waiting time for recv (seconds)
    WAITING_TIME = 5
    server = '127.0.0.1'
    port = 123
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.settimeout(WAITING_TIME)
        packet = NTPPacket()
        s.sendto(packet.pack(), (server, port))

        data = s.recv(48)
        answer = NTPPacket()
        answer.unpack(data)
        arrive_time = time.time() + FORMAT_DIFF
    time_different = answer.get_time_different(arrive_time)
    result = "Time difference: {}\nServer time: {}\n{}".format(
        time_different,
        datetime.datetime.fromtimestamp(time.time() + time_different).strftime("%c"),
        answer.to_display())
    print(result)


if __name__ == '__main__':
    main()