import socket
from .ProtocolPacket import ProtocolPacket
import pickle
import time
import threading

class BootstrapperClient:
    def __init__(self, bootstrapperIP, bootstrapperPort):
        self.bootstrapperIP = bootstrapperIP 
        self.bootstrapperPort = bootstrapperPort

    # description: every 2 seconds send a protocol message to bootstrapper to say that
    # the node yet is alive
    def aliveMessage(self):

        while True:
            try:
                client_socket = socket.socket()
                client_socket.connect((self.bootstrapperIP,self.bootstrapperPort))
                time.sleep(2)
                protocolPacket = ProtocolPacket("1","")
                client_socket.send(pickle.dumps(protocolPacket))
                client_socket.close()
            except:
                client_socket.close()
            finally:
                client_socket.close()

    # description: get current active neighboors and listen to possible neighboors changes
    def getNeighboors(self):
        # socket to initially get current activate neighboors
        client_socket = socket.socket()


        try:
            client_socket.connect((self.bootstrapperIP,self.bootstrapperPort))

            protocolPacket = ProtocolPacket("0","")

            client_socket.send(pickle.dumps(protocolPacket))
            data = client_socket.recv(1024)
            protocolPacket = pickle.loads(data)
            print("Received from server my current active neighboors: ", protocolPacket.data)
        except:
            client_socket.close()
        finally:
            client_socket.close()

        # socket to server can communicate with the client the neighboors changes
        server_socket = socket.socket() 
        server_socket.bind(("0.0.0.0",20003))
        server_socket.listen(2) 

        try:
            while(True):
                print("wait server to send neighboor updates")
                conn, address = server_socket.accept()
                data = conn.recv(1024)
                protocolPacket = pickle.loads(data)
                print("Received from server my new current active neighboor: ", protocolPacket.data)
        except:
            server_socket.close()  
        finally:
            server_socket.close()

    # description: activate getNeighboors and  aliveMessage thread
    def start(self):

        getNeighboorsThread = threading.Thread(target = self.getNeighboors)
        getNeighboorsThread.start()
    
        aliveMessageThread = threading.Thread(target = self.aliveMessage)
        aliveMessageThread.start()