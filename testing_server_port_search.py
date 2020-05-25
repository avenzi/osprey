import socket

host = ''           # allow any connection
port = 80           # TCP port 80
enc = "utf-8"       # byte-style encoding

try:
    ping(host, port)
except:
    pass
            

def ping(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, port))     # bind to ip:port
        s.listen()               # listen for connection
        conn, addr = s.accept()  # accept connection

        with conn:  
            while True:  # loop while data is being received
                data = conn.recv(1024)
                if not data:
                    break

                print(data.decode(enc))
                conn.sendall(b"Received")
                successful.append(port)
