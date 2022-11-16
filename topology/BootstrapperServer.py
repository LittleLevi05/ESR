import socket
from .ConfigTopology import ConfigTopology
from .ProtocolPacket import ProtocolPacket
import pickle
from datetime import datetime, timedelta
import time
import threading

class BootstrapperServer:
    def __init__(self, ip, port, configFile):
        self.ip = ip
        self.port = port
        self.configTopology = ConfigTopology(configFile)

    # description: every 4 seconds check with the nodes in topology send an aliveMesage
    # in the last 4 seconds. If some node X not send and aliveMessage in the
    # last 4 seconds, so the server will send a protocol message with opcode 2
    # for all neighboors of the node X that will indicates that this node is
    # not current activate. 
    def checkAlive(self):
        while True:
            time.sleep(4)
            timeNow = datetime.now() 
            for node in self.configTopology.aliveNodes:
                if self.configTopology.aliveNodes[node] < (timeNow - timedelta(seconds=4)):
                    print(str(node), " is not current alive")
                else:
                    print(str(node), " is current alive")
            print("----------------")

    # [Protocol opcode 0 answer]
    # description: send current actives neihboors from a given node
    # and send to their neighboors the notice that the node is current activate
    def opcode_0_answer(self,conn,address):

        # send current actives neighboors from a given node
        nodeName = self.configTopology.getNodeNameByAddress(address)
        neighboors = self.configTopology.getVizinhos(nodeName)
        activeNeighboors = []

        # update aliveNodes entry with the current node
        self.configTopology.aliveNodes[nodeName] = datetime.now()

        for neighboor in neighboors:
            if self.configTopology.checkIfNodeIsAlive(neighboor["nodo"]) == True:
                activeNeighboors.append(neighboor)

        protocolPacket = ProtocolPacket("3",activeNeighboors)
        conn.send(pickle.dumps(protocolPacket))

        # send to neighboors the notice that the node is current active
        print("Let's send to neighboors from node " + str(nodeName) + " that he is alive!")
        for activeNeighboor in activeNeighboors:
            client_socket = socket.socket()

            try:
                # select a random interface from the active neighboor to send the message
                # here what is relevant is to send the information to the node itself, no matter the interface.
                print("ip a mandar opcode 4: ",activeNeighboor["interfaces"][0]["ip"])
                client_socket.connect((activeNeighboor["interfaces"][0]["ip"],20003))

                # create the packet with the information of the node that is now active
                nodeInterfaces = self.configTopology.getInterfaces(nodeName)
                packet = {}
                packet["nodo"] = nodeName 
                packet["interfaces"] = nodeInterfaces
                protocolPacket = ProtocolPacket("4",packet)

                client_socket.send(pickle.dumps(protocolPacket))
                client_socket.close()
            except Exception as e:
                print(str(e))
                client_socket.close()
            finally:
                client_socket.close()

    # [Protocol opcode 1 answer]
    # description: update the last time that a node made contact with server
    def opcode_1_answer(self,address):
        node = self.configTopology.getNodeNameByAddress(address=address)
        self.configTopology.aliveNodes[node] = datetime.now()
    
    # description: demultiplex diferent protocol requests
    def demultiplexer(self,conn,address):

        data = conn.recv(1024)
        # parser data request into a protocolPacket (opcode + data)
        protocolPacket = pickle.loads(data)
        
        # invoke an action according to the opcode
        if protocolPacket.opcode == '0':
            self.opcode_0_answer(conn=conn, address=address[0])
        elif protocolPacket.opcode == '1':
            self.opcode_1_answer(address=address[0])
        else:
            print("opcode unknown")

    # description: accept new connection, execute demultiplexer for the connection request
    # and activate checkAlive thread
    def start(self):

        server_socket = socket.socket() 
        server_socket.bind((self.ip,self.port))
        server_socket.listen(2) # Número de clientes que o servidor atende simultâneamente

        checkAliveThread = threading.Thread(target = self.checkAlive)
        checkAliveThread.start()

        try:
            while(True):
                conn, address = server_socket.accept()
                self.demultiplexer(conn,address)
        except:
            server_socket.close()  
        finally:
            server_socket.close()

          

            