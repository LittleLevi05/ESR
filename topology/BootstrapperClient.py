import socket
from .ProtocolPacket import ProtocolPacket
import pickle

class BootstrapperClient:
    def __init__(self, bootstrapperIP, bootstrapperPort):
        self.bootstrapperIP = bootstrapperIP 
        self.bootstrapperPort = bootstrapperPort

    def start(self):
        
        client_socket = socket.socket()

        try:
            print("IP Bootstrapper: ",self.bootstrapperIP)
            print("Port Bootstrapper: ",self.bootstrapperPort)
            client_socket.connect((self.bootstrapperIP,self.bootstrapperPort))

            protocolPacket = ProtocolPacket("0","")

            client_socket.send(pickle.dumps(protocolPacket))
            data = client_socket.recv(1024)
            protocolPacket = pickle.loads(data)
            print("Received from server ", protocolPacket.data)
        except:
            client_socket.close()
        finally:
            client_socket.close()