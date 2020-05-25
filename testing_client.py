import socket

host = "3.136.140.191"
port = 8000

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((host, port))
    print("Connected to {}:{}".format(host, port))
    
    test = b'THIS IS A TEST STRING'
    s.sendall(test)
    print("Sent: ", test)
    
    data = s.recv(1024)

print("Received: ", repr(data))
