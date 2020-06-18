import select
import socket
from time import sleep
from threading import Thread

sockets = []
enc = 'utf-8'


def connect(ip=''):
    i = 1
    while True:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # AF_INET = IP, SOCK_STREAM = TCP
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((ip, 5000+i))  # accept any ip on this port
        sock.listen()
        conn, (pi_ip, pi_port) = sock.accept()
        sockets.append(conn)
        print("Created New Socket: {}".format(i))
        i += 1


def read(sock):
    data = sock.recv(64)
    print("Received: \n", data.decode(enc))

    sock.sendall(b'SERVER RESPONSE')
    print("Sent response")


t = Thread(target=connect, daemon=True)
t.start()

while True:
    if sockets:
        sleep(0.5)
        print("Sockets ({}):".format(len(sockets)))

        for s in sockets:
            Thread(target=read, args=(s,), daemon=True).start()


