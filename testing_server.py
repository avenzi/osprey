import socket

host = ''
port = 80
enc = "utf-8"

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    print("Socket Created")
    
    print("Binding to {}:{}".format(host, port))
    s.bind((host, port))
    
    print("Listening")
    s.listen()
    
    conn, addr = s.accept()
    print("Accepted")

    with conn:
        print('Connected by', addr)
        while True:
            data = conn.recv(1024)
            if not data:
                break

            print("Received: \n", data.decode(enc))
            data = data.decode(enc) + "\n THIS LINE WAS SENT FROM THE SERVER"
            data = data.encode(enc)

            conn.sendall(data)
            print("Sent: \n", data.decode(enc))
