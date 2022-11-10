import socket

class Client:
    def __init__(self, serverIP, serverPort):
        self.serverlIP = serverIP
        self.serverPort = serverPort

    # Send and receive datagrams from server
    def start(self):
        print("Send message to server at port:", self.serverPort, "at address:", self.serverlIP)
        
        msgFromClient = "Hello UDP Server"
        bytesToSend = str.encode(msgFromClient)

        # Create a UDP socket at client side
        UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        # Send to server using created UDP socket
        UDPClientSocket.sendto(bytesToSend, (self.serverlIP, self.serverPort))

        msgFromServer = UDPClientSocket.recvfrom(1024)
        msg = "Message from Server {}".format(msgFromServer[0])
        print(msg)