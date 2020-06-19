import socket
from time import sleep
from threading import Thread

host = "35.11.244.179"  # public ip of Ubuntu server
port = 5000
enc = "utf-8"  # byte encoding


def create(n, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))  # connect to given ip and port
    print("Connected to {}:{}\n".format(host, port))
    while True:
        sleep(1)
        test = b'THIS STRING SENT FROM CLIENT'  # testing string to send
        sock.sendall(test)
        print("Sent from {}: {}\n".format(n, test.decode(enc)))
        while True:
            try:
                data = sock.recv(128)  # receive response
            except BlockingIOError:
                pass
            else:
                print("Received at {}: {}\n".format(n, data.decode(enc)))
                break


for n in [1, 2, 3, 4, 5]:
    t = Thread(target=create, args=(n, 5000+n), daemon=True)
    t.start()

