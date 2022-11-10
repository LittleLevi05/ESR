import socket

class Bootstrapper:
    def __init__(self, localIP, localPort, configFile):
        self.localIP = localIP
        self.localPort = localPort
        self.configFile = configFile

    # Listen for incoming datagrams
    def start(self):
        msgFromServer = "Hello UDP Client"
        bytesToSend = str.encode(msgFromServer)

        # Create a datagram socket
        UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        # Bind to address and ip
        UDPServerSocket.bind((self.localIP, self.localPort))

        print("Bootstrap UDP server up and listening to send Configurations")
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