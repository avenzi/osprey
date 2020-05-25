import socket

host = "3.136.140.191"
port = 80
enc = "utf-8"

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((host, port))
    print("Connected to {}:{}".format(host, port))
    
    test = b'THIS STRING SENT FROM CLIENT'
    s.sendall(test)
    print("Sent: \n", test.decode(enc))
    
    data = s.recv(1024)

print("Received: \n", data.decode(enc))
