import socket

host = "3.136.140.191"  # public ip of Ubuntu server
port = 80               # TCP port 80
enc = "utf-8"           # hyte style encoding

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((host, port))  # connect to given ip and port
    print("Connected to {}:{}".format(host, port))
    
    test = b'THIS STRING SENT FROM CLIENT'  # testing string to send
    s.sendall(test)
    print("Sent: \n", test.decode(enc))
    
    data = s.recv(1024)  # receive response

print("Received: \n", data.decode(enc))
