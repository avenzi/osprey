import socket
import time

host = "35.11.244.179"  # public ip of Ubuntu server
port = 5001             
enc = "utf-8"           # byte encoding

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((host, port))  # connect to given ip and port
    s.setblocking(False)
    print("Connected to {}:{}".format(host, port))
    
    while True:
        try:
            data = s.recv(1024)
            print("got {}".format(data))
        except BlockingIOError:
            pass
        
        try:
            s.sendall(b"FROM PI")
            print("sent")
            time.sleep(0.5)
        except BlockingIOError:
            pass
            
print("Received: \n", data.decode(enc))


