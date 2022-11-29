import socket
from .ProtocolPacket import ProtocolPacket
import pickle
import time
import threading
from datetime import datetime
import sys

class BootstrapperClient:
    def __init__(self, bootstrapperIP, bootstrapperPort):
        self.bootstrapperIP = bootstrapperIP 
        self.bootstrapperPort = bootstrapperPort
        self.groups = {}
        self.servers = {}
        self.aliveNeighbours = {}
        self.metricsConstruction = {}
        # Need to initialize at 0 for every aliveNeighbour
        self.metricsEphocs = {}

    def getNeighboorNameByAddress(self, address):
        for node in self.aliveNeighbours:
            for interface in self.aliveNeighbours[node]:
                if interface["ip"] == address:
                    return node

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
        self.aliveNeighbours.pop(str(protocolPacket.data["nodo"]))
        print("Active nodes update ----------------------------")
        print(self.aliveNeighbours)

    def opcode_4_handler(self,protocolPacket):
        # print("opcode 4!")
        # print("Nodo ", str(protocolPacket.data["nodo"]), " está ativo!")
        self.aliveNeighbours[str(protocolPacket.data["nodo"])] = protocolPacket.data["interfaces"]
        print("Active nodes update ----------------------------")
        print(self.aliveNeighbours)

    def opcode_5_handler(self,protocolPacket, address):
        
        # update metric from address node
        neighboorName = self.getNeighboorNameByAddress(address)
        metricsConstruction = {}
        metricsConstruction["saltos"] = protocolPacket.data["saltos"]
        metricsConstruction["tempo"] =  datetime.now() - protocolPacket.data["tempo"]
        self.metricsConstruction[neighboorName] = metricsConstruction

        # send probe packets to neighboors except address node
        for activeNeighboor in self.aliveNeighbours:
            if activeNeighboor != neighboorName:
                try:
                    client_socket = socket.socket()
                    # select a random interface from the active neighboor to send the message
                    # here what is relevant is to send the information to the node itself, no matter the interface.
                    client_socket.connect((self.aliveNeighbours[activeNeighboor][0]["ip"],20003))
                    print(rootNode)
                    data = {}
                    data["saltos"] = protocolPacket.data["saltos"] + 1
                    data["tempo"] =  protocolPacket.data["tempo"]
                    protocolPacket = ProtocolPacket("5",data)
                    client_socket.send(pickle.dumps(protocolPacket))
                except Exception as e:
                    print(str(e))
                finally:
                    client_socket.close()
    def opcode_6_handler(self, protocolPacket):
        """I'm a root node and need to start a flood to update metrics to servers im rooting"""
        print("Received a flood metrics request")
        data = protocolPacket.data
        servers = data["servidores"]
        for aliveNeighbour in self.aliveNeighbours:
            try:
                client_socket = socket.socket()
                print("Alive neigbours ip " + self.aliveNeighbours[aliveneighbour][0]["ip"])
                client_socket.connect((self.aliveNeighbours[aliveNeighbour][0]["ip"], 20003))
                data = {}
                # for now this will be considered as an approximate metric of
                # time to the servers although it should be updated to a round trip
                # ping pong request to the servers
                for server in servers:
                    data[server] = {"saltos": 0, "rtt": datetime.now()}

                protocolPacket = ProtocolPacket("7", data)
                client_socket.send(pickle.dumps(protocolPacket))
            except Exception as e:
                print(str(e))
            finally:
                client_socket.close()

    def opcode_7_handler(self, protocolPacket, address):
        """I'm an overlay layer and need to update my metrics and continue to flood"""
        print("I'm here")
        neighbourName = self.getNeighboorNameByAddress(address)

        data = protocolPacket.data

        #update my own server metrics
        for server, server_info in data.items():
            server_info = self.updateMetricsByServer(server, server_info, address)

        for alive in self.aliveNeighbours:
            if alive != neighbourName:
                try:
                    client_socket = socket.socket()
                    client_socket.connect((self.aliveNeighbours[alive][0]["ip"],20003))

                    protocolPacket = ProtocolPacket("7", data)
                    client_socket.send(pickle.dumps(protocolPacket))
                except Exception as e:
                    print(str(e))
                finally:
                    client_socket.close()


    def updateMetricsByServer(server, server_info, address):
        """ server layout : 's1' ex. server_info : { 'saltos': 0, 'rtt' : time.now() }"""
        """ self.metricsConstruction layout :{ 's2' : {'saltos' : {'value' : 2, 'node' : 'n1', 'epoch' : 3}, 'rtt' { 'value' : datetime.now(), 'node' : 'n2', 'epoch' : 2}}} """

        neighbourName = self.getNeighboorNameByAddress(address)
        metrics_info = self.metricsConstruction
        saltos_present = metrics_info[server]["saltos"]["value"]
        rtt_present = metrics_info[server]["rtt"]["value"]
        saltos_arg = server_info["saltos"]
        rtt_arg = server_info["rtt"]

        rtt_new = datetime.now() - rtt_arg
        saltos_new = saltos_arg + 1

        #for all metrics check if there is a better metric
        # TODO Há o problema em que tenho que atualizar a métrica para cada iteração
        # Posso criar uma noção de épocas e comparar épocas de métricas.
        # Assume-se a inicialização de estruturas
        self.metricsEphocs[neighbourName] += 1

        rtt_updated_dic = {"value" : rtt_new, "node" : neighbourName, "ephocs" : self.metricsEphocs[neighbourName]}
        saltos_updated_dic = {"value" : saltos_new, "node" : neighbourName, "ephocs" : self.metricsEphocs[neighbourName]}
        #first update outdated metrics
        if metrics_info[server]["rtt"]["ephoc"] < self.metricsEphocs[neighbourName] or rtt_new < rtt_present:
            metrics_info[server]["rtt"] = rtt_updated_dic

        if metrics_info[server]["saltos"]["ephoc"] < self.metricsEphocs[neighbourName] or saltos_new < saltos_present:
            metrics_info[server]["saltos"] = saltos_updated_dic

        server_info["saltos"] += 1
        #server_info["rtt"] mantains the same since the goal is to have the original timestamp of the root node, for now.

        return server_info

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
            elif protocolPacket.opcode == '5':
                self.opcode_5_handler(protocolPacket = protocolPacket, address=address[0])
            elif protocolPacket.opcode == '6':
                self.opcode_6_handler(protocolPacket = protocolPacket)
            else:
                print("opcode unknown")
        except EOFError:
            print("EOF error")

    # description: 
    #  1-) get current active neighboors 
    #  2-) listen to possible neighboors changes
    #  3-) listen to probe packets 
    def service(self):
        # socket to initially get current activate neighboors
        client_socket = socket.socket()

        try:
            client_socket.connect((self.bootstrapperIP,self.bootstrapperPort))

            #ask for info of alive Neighbours
            protocolPacket = ProtocolPacket("0","")
            print("sent info")
            client_socket.send(pickle.dumps(protocolPacket))
            #recieve info
            data = client_socket.recv(1024)
            protocolPacket = pickle.loads(data)


            print("Received from server my current active neighboors: ", protocolPacket.data)
            for node in protocolPacket.data:
                self.aliveNeighbours[node["nodo"]] = node["interfaces"]
            #ask for info of current servers and current groups

            client_socket.close()
            client_socket = socket.socket()
            client_socket.connect((self.bootstrapperIP,self.bootstrapperPort))

            protocolPacket = ProtocolPacket("2","")
            client_socket.send(pickle.dumps(protocolPacket))
            protocolPacket = client_socket.recv(1024)
            data = pickle.loads(protocolPacket).data


            #init server structure
            print(data)
            print("Received from server the initial server and group configuration")
            self.servers = data["server_info"]
            print(data["server_info"])
            #init group structure
            self.groups = data["group_info"]
            print(data["group_info"])

            #init metricsConstructions with max values
            for server, server_info in self.servers.keys():
                self.metricsConstruction[server]["saltos"]["value"] = sys.maxsize
                self.metricsConstruction[server]["rtt"]["value"] = datetime.now()

            for node in self.aliveNeighbours:
                self.metricsEphocs[node] = 0

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
        finally:
            server_socket.close()

    # description: activate getNeighboors and  aliveMessage thread
    def start(self):

        serviceThread = threading.Thread(target = self.service)
        serviceThread.start()
    
        aliveMessageThread = threading.Thread(target = self.aliveMessage)
        aliveMessageThread.start()
