import socket

host = ''           # allow any connection
port = 5000
enc = "utf-8"       # byte encoding

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    print("Binding to {}:{}".format(host, port))
    s.bind((host, port))
    
    print("Listening")
    s.listen()
    
    conn, addr = s.accept()
    print("Accepted")

    with conn:
        print('Connected by', addr)
        while True:  # loop while data is being received
            data = conn.recv(1024)
            if not data:
                break

            print("Received: \n", data.decode(enc))

            # add message to send back
            data = data.decode(enc) + "\n THIS LINE WAS SENT FROM THE SERVER"
            data = data.encode(enc)  # encode back into byte object

            conn.sendall(data)
            print("Sent: \n", data.decode(enc))
