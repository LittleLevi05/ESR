import socket
from .ProtocolPacket import ProtocolPacket
import pickle
import time
import threading

class BootstrapperClient:
    def __init__(self, bootstrapperIP, bootstrapperPort):
        self.bootstrapperIP = bootstrapperIP 
        self.bootstrapperPort = bootstrapperPort
        self.activeNeighboors = {}

    # description: every 2 seconds send a protocol message to bootstrapper to say that
    # the node yet is alive
    def aliveMessage(self):

        while True:
            try:
                client_socket = socket.socket()
                client_socket.connect((self.bootstrapperIP,self.bootstrapperPort))
                time.sleep(2)
                # print("let's send alive message!")
                protocolPacket = ProtocolPacket("1","")
                client_socket.send(pickle.dumps(protocolPacket))
                client_socket.close()
            except Exception as e:
                print(str(e))
                client_socket.close()
            finally:
                client_socket.close()

    def opcode_3_handler(self,protocolPacket):
        # print("opcode 3!")
        # print(protocolPacket.data)
        # print("Nodo ", str(protocolPacket.data["nodo"], " está desativo!"))
        self.activeNeighboors.pop(str(protocolPacket.data["nodo"]))
        print("Active nodes update ----------------------------")
        print(self.activeNeighboors)

    def opcode_4_handler(self,protocolPacket):
        # print("opcode 4!")
        # print("Nodo ", str(protocolPacket.data["nodo"]), " está ativo!")
        self.activeNeighboors[str(protocolPacket.data["nodo"])] = protocolPacket.data["interfaces"]
        print("Active nodes update ----------------------------")
        print(self.activeNeighboors)

    # description: demultiplex diferent protocol requests
    def demultiplexer(self,conn,address):

        data = conn.recv(1024)
        try:
            # parser data request into a protocolPacket (opcode + data)
            protocolPacket = pickle.loads(data)
        
            # invoke an action according to the opcode
            if protocolPacket.opcode == '3':
                self.opcode_3_handler(protocolPacket = protocolPacket)
            elif protocolPacket.opcode == '4':
                self.opcode_4_handler(protocolPacket = protocolPacket)
            else:
                print("opcode unknown")
        except EOFError:
            print("EOF error")

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
            for node in protocolPacket.data:
                self.activeNeighboors[node["nodo"]] = node["interfaces"]
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
                self.demultiplexer(conn,address)
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