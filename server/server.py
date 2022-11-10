import socket

class Server:
    def __init__(self, localIP, localPort):
        self.localIP = localIP
        self.localPort = localPort

    # Listen for incoming datagrams
    def start(self):
        msgFromServer = "Hello UDP Client"
        bytesToSend = str.encode(msgFromServer)

        # Create a datagram socket
        UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        # Bind to address and ip
        UDPServerSocket.bind((self.localIP, self.localPort))

        print("UDP server up and listening in port:", self.localPort, "at address:", self.localIP)
        while(True):

            bytesAddressPair = UDPServerSocket.recvfrom(1024)

            message = bytesAddressPair[0]

            address = bytesAddressPair[1]

            clientMsg = "Message from Client:{}".format(message)
            clientIP  = "Client IP Address:{}".format(address)
            
            print(clientMsg)
            print(clientIP)

            # Sending a reply to client
            UDPServerSocket.sendto(bytesToSend, address)