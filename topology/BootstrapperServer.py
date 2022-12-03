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
        self.lock = threading.RLock

    def isBootstrapper(self, interfaces):
        for interface in interfaces:
            if interface["ip"] == self.ip:
                return True 
        return False

    # description: every 4 seconds check with the nodes in topology send an aliveMesage
    # in the last 4 seconds. If some node X not send and aliveMessage in the
    # last 4 seconds, so the server will send a protocol message with opcode 2
    # for all neighboors of the node X that will indicates that this node is
    # not current activate. 
    def checkAlive(self):
        while True:
            nodesNotAlive = []
            time.sleep(6)
            timeNow = datetime.now() 

            try:
                self.lock.acquire()
                node = self.configTopology.getNodeNameByAddress(address=self.ip)
                self.configTopology.aliveNodes[node] = timeNow

                for node in self.configTopology.aliveNodes:
                    # print("nodo:", str(node)," - last time:", str(self.configTopology.aliveNodes[node]))
                    if self.configTopology.aliveNodes[node] < (timeNow - timedelta(seconds=6)):
                        print(str(node), " is not current alive")
                        nodesNotAlive.append(node)
                        for neighboor in self.configTopology.getVizinhos(str(node)):
                            print("devo avisar ao ", str(neighboor), " que o ", str(node), "não está mais ativo!")
                            try:
                                client_socket = socket.socket()
                                # select a random interface from the active neighboor to send the message
                                # here what is relevant is to send the information to the node itself, no matter the interface.
                                client_socket.connect((neighboor["interfaces"][0]["ip"],20003))
                                data = {}
                                data["nodo"] = str(node)
                                protocolPacket = ProtocolPacket("3",data)
                                client_socket.send(pickle.dumps(protocolPacket))
                            except Exception as e:
                                print(str(e))
                                client_socket.close()
                            finally:
                                client_socket.close()
                        else:
                            print(str(node), " is current alive")

                            # eliminate nodes not actives
                            for node in nodesNotAlive:
                                self.configTopology.aliveNodes.pop(node)
            finally:
                self.lock.release()
            print("----------------")

    # description: in a first view, assuming Bootstrapper node is the RP node of the 
    # shared tree, every 4 seconds will be send a prove packet to all routes in the
    # system. Control floading will be used, so the RP node only need to send the
    # probe packet to their neighboors.
    def probePacket(self):
        while True:
            time.sleep(4)
            timeNow = datetime.now()
            try:
                self.lock.acquire()
                nodeName = self.configTopology.getNodeNameByAddress(self.ip)
                neighboors = self.configTopology.getVizinhos(nodeName=nodeName)
                for neighboor in neighboors:
                    if neighboor["nodo"] in self.configTopology.aliveNodes:
                        try:
                            client_socket = socket.socket()
                            # select a random interface from the active neighboor to send the message
                            # here what is relevant is to send the information to the node itself, no matter the interface.
                            print("neighbour interface " + neighboor["interfaces"][0]["ip"])
                            client_socket.connect((neighboor["interfaces"][0]["ip"],20003))
                            data = {}
                            data["saltos"] = 0
                            data["tempo"] = timeNow
                            protocolPacket = ProtocolPacket("5",data)
                            client_socket.send(pickle.dumps(protocolPacket))
                        except Exception as e:
                            print(str(e))
                            client_socket.close()
                        finally:
                            client_socket.close()
            finally:
                self.lock.release()

    # [Protocol opcode 0 answer]
    # description: send current actives neihboors from a given node
    # and send to their neighboors the notice that the node is current activate
    def opcode_0_answer(self,conn,address):

        # send current actives neighboors from a given node
        try:
            self.lock.acquire()
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
                    # print("Let's send to neighboors from node " + str(nodeName) + " that he is alive!")
                    for activeNeighboor in activeNeighboors:
                        client_socket = socket.socket()

                        if not self.isBootstrapper(activeNeighboor["interfaces"]):
                            try:
                                # select a random interface from the active neighboor to send the message
                                # here what is relevant is to send the information to the node itself, no matter the interface.
                                # print("ip a mandar opcode 4: ",activeNeighboor["interfaces"][0]["ip"])
                                client_socket.connect((activeNeighboor["interfaces"][0]["ip"],20003))

                                # create the packet with the information of the node that is now active
                                nodeInterfaces = self.configTopology.getInterfaces(nodeName)
                                packet = {}
                                packet["nodo"] = nodeName
                                packet["interfaces"] = nodeInterfaces
                                protocolPacket = ProtocolPacket("4",packet)

                                client_socket.send(pickle.dumps(protocolPacket))
                            except Exception as e:
                                print(str(e))
                                client_socket.close()
                            finally:
                                client_socket.close()
        finally:
            self.lock.release()

    # [Protocol opcode 1 answer]
    # description: update the last time that a node made contact with server
    def opcode_1_answer(self,address):
        try:
            self.lock.acquire()
            node = self.configTopology.getNodeNameByAddress(address=address)
            self.configTopology.aliveNodes[node] = datetime.now()
        finally:
            self.lock.release()

    # [Protocol opcode 2 answer]
    # description: return a dictionary with group and server info
    def opcode_2_answer(self, conn, address):
        data = {}
        try:
            self.lock.acquire()
            data["server_info"] = self.configTopology.getServers()
            data["group_info"] = self.configTopology.getGroups()

            # opcode -1 because this is only supposed to be used on initiation
            # when there is a change in groups and server an alert on the modification
            # will be sent
            protocolPacket = ProtocolPacket("-1",data)
            print("Sending initial server and group information")
            conn.send(pickle.dumps(protocolPacket))
        finally:
            self.lock.release()


    
    # description: demultiplex diferent protocol requests
    def demultiplexer(self,conn,address):

        data = conn.recv(1024)
        try:
            # parser data request into a protocolPacket (opcode + data)
            protocolPacket = pickle.loads(data)
        
            # invoke an action according to the opcode
            if protocolPacket.opcode == '0':
                self.opcode_0_answer(conn=conn, address=address[0])
            elif protocolPacket.opcode == '1':
                # print("receive opcode 1")
                self.opcode_1_answer(address=address[0])
            elif protocolPacket.opcode == '2':
                self.opcode_2_answer(conn=conn, address=address[0])
            else:
                print("opcode unknown")
        except EOFError:
            print("EOF error")

    def rootNodesProbeReminder(self):
        while True:
            time.sleep(9)
            try:
                self.lock.acquire()
                rootsAndServers = self.configTopology.getRootNodesAndServers()
                for rootNode, servers in rootsAndServers.items():
                    if rootNode in self.configTopology.aliveNodes:
                        client_socket = socket.socket()
                        try:
                            client_socket.connect((self.configTopology.getRandomInterface(rootNode), 20003))

                            packet = {}
                            packet["servidores"] = servers
                            print("Sent protocolPacket with opcode 6")

                            protocolPacket = ProtocolPacket("6", packet)
                            client_socket.sendall(pickle.dumps(protocolPacket))
                        except Exception as e:
                            print(str(e))
                        finally:
                            client_socket.close()
            finally:
                self.lock.release()

    # description: 
    #   1-) accept new connection, execute demultiplexer for the connection request
    #   2-) activate checkAlive thread
    #   3-) activate probePacket thread
    #   4-) activate rootNodesProbeReminder thread
    def start(self):

        server_socket = socket.socket() 
        server_socket.bind((self.ip,self.port))
        server_socket.listen(2) # Número de clientes que o servidor atende simultâneamente

        node = self.configTopology.getNodeNameByAddress(address=self.ip)
        self.configTopology.aliveNodes[node] = datetime.now()

        checkAliveThread = threading.Thread(target = self.checkAlive)
        checkAliveThread.start()
        probePacketThread = threading.Thread(target = self.probePacket)
        probePacketThread.start()
        rootNodesReminderThread = threading.Thread(target = self.rootNodesProbeReminder)
        rootNodesReminderThread.start()

        try:
            while(True):
                conn, address = server_socket.accept()
                self.demultiplexer(conn,address)
        except Exception as e:
            print(str(e))
            server_socket.close()  
        finally:
            server_socket.close()
