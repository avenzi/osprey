import socket, time

host = ''  # allow any connection
port = 5001  # TCP port 80
enc = "utf-8"  # byte encoding

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    print("Binding to {}:{}".format(host, port))
    s.bind((host, port))

    print("Listening")
    s.listen()

    conn, addr = s.accept()
    print("Accepted")
    conn.setblocking(False)

    with conn:
        print('Connected by', addr)
        i = 0
        while True:
            i += 1
            try:
                conn.sendall("THIS IS A TEST {}".format(i).encode(enc))
                print("sent")
                time.sleep(0.5)
            except BlockingIOError:
                pass

            try:
                data = conn.recv(1024)
                print("got: {}".format(data))
            except BlockingIOError:
                pass


