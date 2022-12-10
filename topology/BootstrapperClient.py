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
        self.aliveClients = {}
        self.clientNo = 0
        self.metricsConstruction = {}
        # Need to initialize at 0 for every aliveNeighbour
        self.metricsEpochs = {}
        self.activeClientsByNode = {}
        self.metricsGroup = {}
        self.lock = threading.Lock()
        self.metrics = ["rtt", "saltos"]
        self.entryPoint = False

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
                time.sleep(2)
                client_socket = socket.socket()
                client_socket.settimeout(1)
                client_socket.connect((self.bootstrapperIP,self.bootstrapperPort))
                # print("let's send alive message!")
                protocolPacket = ProtocolPacket("1","")
                client_socket.send(pickle.dumps(protocolPacket))
            except Exception as e:
                print("Estou aqui AliveMessage")
            finally:
                client_socket.close()

    def opcode_3_handler(self,protocolPacket):
        print("opcode 3!")
        print(protocolPacket.data)
        print("Nodo ", protocolPacket.data["nodo"], " está desativo!")
        if protocolPacket.data["nodo"] in self.aliveNeighbours.keys():
            self.aliveNeighbours.pop(protocolPacket.data["nodo"])
        print("Active nodes update ----------------------------")
        print(self.aliveNeighbours)

    def opcode_4_handler(self,protocolPacket):
        # print("opcode 4!")
        # print("Nodo ", str(protocolPacket.data["nodo"]), " está ativo!")
        self.aliveNeighbours[str(protocolPacket.data["nodo"])] = protocolPacket.data["interfaces"]
        self.metricsEpochs[protocolPacket.data["nodo"]] = self.getMaxEpoch()

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
                    data = {}
                    data["saltos"] = protocolPacket.data["saltos"] + 1
                    data["tempo"] =  protocolPacket.data["tempo"]
                    protocolPacket = ProtocolPacket("5",data)
                    client_socket.send(pickle.dumps(protocolPacket))
                except Exception as e:
                    print("Estou aqui 5")
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
                client_socket.settimeout(1)
                #print("Alive neigbours ip " + self.aliveNeighbours[aliveNeighbour][0]["ip"])
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
                print("Estou aqui 6")
            finally:
                client_socket.close()

    def opcode_7_handler(self, protocolPacket, address):
        """I'm an overlay layer and need to update my metrics and continue to flood"""
        neighbourName = self.getNeighboorNameByAddress(address)

        data = protocolPacket.data

        old_group_metrics = self.metricsGroup.copy()
        print("OUTDATED METRICS" + str(self.metricsConstruction))
        #update my own server metrics
        for server, server_info in data.items():
            server_info = self.updateMetricsByServer(server, server_info, address)

        for group in self.groups:
            self.updateNodeByGroup(group)

        new_group_metrics = self.metricsGroup.copy()

        #Send to the above nodes that I no longer need some connections or request new connections based on active groups.
        #Check all the groups that have at least one client using them and request to the new best node, and cut to the previous node

        print("UPDATED METRICS" + str(self.metricsConstruction))

        print("UPDATED METRICS GROUP" + str(self.metricsGroup))


        
        if self.anyClientActive():
            self.sendChangesMessages(old_group_metrics, new_group_metrics)

        iteration_neigh = self.aliveNeighbours.copy()

        for alive in iteration_neigh:
            if alive != neighbourName:
                client_socket = socket.socket()
                client_socket.settimeout(1)
                try:
                    client_socket.connect((self.aliveNeighbours[alive][0]["ip"],20003))
                    protocolPacket = ProtocolPacket("7", data)
                    client_socket.send(pickle.dumps(protocolPacket))
                except Exception as e:
                    print("Estou aqui 7")
                finally:
                    client_socket.close()


    def anyClientActive(self):
        print("ACTIVE CLIENTS: " + str(self.activeClientsByNode))
        for node in self.activeClientsByNode.keys():
            for metric in self.activeClientsByNode[node].keys():
                for group in self.activeClientsByNode[node][metric].keys():
                    if self.activeClientsByNode[node][metric][group] > 0:
                        return True
        
        return False



    def sendChangesMessages(self, old, new):
        # Lembrar que no futuro se houver adição de grupos dinâmicos tenho que
        # garantir que self.groups é atualizado
        #iterate through groups
        print("OLD: " + str(old))
        print("NEW: " + str(new))

        if len(old) == 0:
            return

        for group in self.groups.keys():
            for metric in self.metrics:
                #there was a change, need to send messages
                old_node = old[group][metric]
                new_node = new[group][metric]
                if old_node != new_node:
                    # Send protocol message number 8 to indicate I want
                    # to listen to a new stream
                    client_socket = socket.socket()
                    client_socket.settimeout(1)
                    try:
                        client_socket.connect((self.aliveNeighbours[new_node][0]["ip"], 20003))
                        data = {}
                        data["group"] = group
                        data["metric"] = metric
                        data["action"] = "START"
                        protocolPacket = ProtocolPacket("8", data)
                        client_socket.send(pickle.dumps(protocolPacket))
                    except Exception as e:
                        print("Estou aqui enviar que quero um grupo")
                    finally:
                        client_socket.close()

                    # Send protocol message number 9 to indicate I
                    # No longer want to listen to the old stream group
                    client_socket = socket.socket()
                    client_socket.settimeout(1)
                    try:
                        client_socket.connect((self.aliveNeighbours[old_node][0]["ip"], 20003))
                        data = {}
                        data["group"] = group
                        data["metric"] = metric
                        data["action"] = "STOP"
                        protocolPacket = ProtocolPacket("8", data)
                        client_socket.send(pickle.dumps(protocolPacket))
                    except Exception as e:
                        print("Estou aqui enviar que já não quero um grupo")
                    finally:
                        client_socket.close()


    def getMaxEpoch(self):
        r = 0
        for epochs in self.metricsEpochs.values():
            if epochs > r: 
                r = epochs
        
        return r
        

    def updateMetricsByServer(self, server, server_info, address):
        """ server layout : 's1' ex. server_info : { 'saltos': 0, 'rtt' : time.now() }"""
        """ self.metricsConstruction layout :{ 's2' : {'saltos' : {'value' : 2, 'node' : 'n1', 'epoch' : 3}, 'rtt' { 'value' : datetime.now(), 'node' : 'n2', 'epoch' : 2}}} """

        #send to neighbours

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
        self.metricsEpochs[neighbourName] += 1

        rtt_updated_dic = {"value" : rtt_new, "node" : neighbourName, "epoch" : self.metricsEpochs[neighbourName]}
        saltos_updated_dic = {"value" : saltos_new, "node" : neighbourName, "epoch" : self.metricsEpochs[neighbourName]}
        #first update outdated metrics
        if metrics_info[server]["rtt"]["epoch"] < self.metricsEpochs[neighbourName] or rtt_new < rtt_present:
            metrics_info[server]["rtt"] = rtt_updated_dic

        if metrics_info[server]["saltos"]["epoch"] < self.metricsEpochs[neighbourName] or saltos_new < saltos_present:
            metrics_info[server]["saltos"] = saltos_updated_dic

        server_info["saltos"] += 1
        #server_info["rtt"] mantains the same since the goal is to have the original timestamp of the root node, for now.



        return server_info

    def opcode_8_handler(self, protocolPacket, address):
        """I'm a overlay layer node and received a message to create or a remove  connection with you"""
        #self.activeClientsByNode add mais um
        node = self.getNeighboorNameByAddress(address)

        data = protocolPacket.data
        group = data["group"]
        metric = data["metric"]
        action = data["action"]

        self.checkAndInitActiveClients(node, metric, group)

        if action == "STOP":
            cur = max(0, cur - 1)
        elif action == "START":
            cur += 1
        else:
            pass

        self.activeClientsByNode[node][metric][group] = cur


    def opcode_9_handler(self, protocolPacket, address):
        """ I'm a overlay node and a client decided to stopped/requested to watch a stream.
        Need to tell my best neighbour for each metric (way to the root) """
        # make functions to check init and init
        # make function to update active interfaces

        if not self.entryPoint:
            node = self.getNeighboorNameByAddress(address)
        else:
            node = self.getClient(address)

        data = protocolPacket.data
        group = data["group"]
        metric = data["metric"]
        action = data["action"]
        self.checkAndInitActiveClients(node, metric, group)

        cur = self.activeClientsByNode[node][metric][group]
        if action == "STOP":
            cur = max(0, cur - 1)
        elif action == "START":
            cur += 1
        else:
            pass

        self.activeClientsByNode[node][metric][group] = cur

        parent_node = self.metricsGroup[group][metric]

        client_socket = socket.socket()
        client_socket.settimeout(1)

        try:
            client_socket.connect((self.aliveNeighbours[parent_node][0]["ip"],20003))
            protocolPacket = ProtocolPacket("9", data)
            client_socket.send(pickle.dumps(protocolPacket))
        except Exception as e:
            print("Estou aqui 9")
        finally:
            client_socket.close()

    def sendRequestPacket(self, node, data, opcode):
        client_socket = socket.socket()
        client_socket.settimeout(1)

        try:
            client_socket.connect((self.aliveNeighbours[node][0]["ip"],20003))
            protocolPacket = ProtocolPacket(opcode, data)
            client_socket.send(pickle.dumps(protocolPacket))
        except Exception as e:
            print("Estou aqui " + opcode)
        finally:
            client_socket.close()

    def opcode_10_handler(self, protocolPacket, address):
        """ A client requested to create a session, if I'm not a Entry point
        I'll become one"""
        self.entryPoint = True
        client_name = "c" + str(self.clientNo)
        self.clientNo +=1
        self.aliveClients[client_name] = address

    def opcode_11_handler(self, protocolPacket, address):
        """I'm an entryPoint and I'll remove a client"""
        """If I get no clients I'll no longer be an entryPoint"""

        if self.entryPoint:
            client = self.getClient(address)

            if client != None:
                #remove client from activeInterfaces
                if client in self.activeClientsByNode.keys():
                    data = {}
                    data["action"] = "STOP"
                    #If the client didn't pause we will
                    #Will send the stop request for my parent nodes
                    for metric in activeClientsByNode[client]:
                        data["metric"] = metric
                        for group in activeClientsByNode[group]:
                            data["group"] = group
                            parent_node = self.metricsGroup[group][metric]
                            self.sendRequestPacket(parent_node, data, "9")

                    self.activeClientsByNode.pop(client)

                #remove client from client with a session
                self.aliveClients.pop(client)
                if len(self.aliveClients) == 0:
                    self.entryPoint = False


    def getClient(self, address):
        for client, ip in self.aliveClients.items():
            if ip == adress:
                return client

    def checkAndInitActiveClients(self, node, metric, group):
        # init if new node
        if node not in self.activeClientsByNode.keys():
            self.activeClientsByNode[node] = {}

        # init if new metric
        if metric not in self.activeClientsByNode[node].keys():
            self.activeClientsByNode[node][metric] = {}

        # init if new group
        if group not in self.activeClientsByNode[node][metric].keys():
            self.activeClientsByNode[node][metric][group] = 0

    # description: demultiplex diferent protocol requests
    def demultiplexer(self,conn,address):

        try:
            data = conn.recv(1024)
            # parser data request into a protocolPacket (opcode + data)
            protocolPacket = pickle.loads(data)
         
            self.lock.acquire()
           
            # invoke an action according to the opcode
            if protocolPacket.opcode == '3':
                self.opcode_3_handler(protocolPacket = protocolPacket)
            elif protocolPacket.opcode == '4':
                self.opcode_4_handler(protocolPacket = protocolPacket)
            elif protocolPacket.opcode == '5':
                self.opcode_5_handler(protocolPacket = protocolPacket, address=address[0])
            elif protocolPacket.opcode == '6':
                self.opcode_6_handler(protocolPacket = protocolPacket)
            elif protocolPacket.opcode == '7':
                self.opcode_7_handler(protocolPacket = protocolPacket, address=address[0])
            elif protocolPacket.opcode == '8':
                self.opcode_8_handler(protocolPacket = protocolPacket, address = address[0])
            elif protocolPacket.opcode == '9':
                self.opcode_9_handler(protocolPacket= protocolPacket, address = address)
            elif protocolPacket.opcode == '10':
                self.opcode_10_handler(protocolPacket = protocolPacket, address = address)
            elif protocolPacket.opcode == '11':
                self.opcode_11_handler(protocolPacket, address)
            else:
                print("opcode unknown")
        except EOFError:
            print("EOF error")
        except socket.error:
            conn.close()
        finally:
            self.lock.release()

    # description: 
    #  1-) get current active neighboors 
    #  2-) listen to possible neighboors changes
    #  3-) listen to probe packets 
    def service(self):
        # socket to initially get current activate neighboors

        try:
            self.lock.acquire()
            client_socket = socket.socket()
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
            # Structure self.groups = { group_no : ["s3", "s1", "s4"] }
            self.groups = data["group_info"]
            print(data["group_info"])

            #init metricsConstructions with max values
            for server in self.servers.keys():
                self.metricsConstruction[server] = {"saltos" : {"value" : sys.maxsize, "epoch" : 0} , "rtt": {"value" : datetime.now(), "epoch" : 0}}

            for node in self.aliveNeighbours:
                self.metricsEpochs[node] = 0

            ## Structure helf.activeClientsByNode = { neighbour_node : { metric : {group_no : count } }}
            #for node in self.aliveNeighbours:
            #    groups_count = {}
            #    for metric in self.metrics:
            #        for group in self.groups:
            #            groups_count[metric][group] = 0
            #    self.activeClientsByNode[node] = groups_count

        finally:
            client_socket.close()
            self.lock.release()

        # socket to server can communicate with the client the neighboors changes
        
        
        

        try:
            server_socket = socket.socket() 
            server_socket.bind(("0.0.0.0",20003))
            server_socket.listen(2) 
            
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


    #routing functions
    def getClosestNeighbour(self, group, metric):
        servers = self.groups[group]
        node_min = self.getMinNode(servers, metric)
        return node_min



    # Por testar
    def getMinNode(self, servers, metric):
        servers_aux = servers.copy()
        min = None
        node_min = None
        if len(servers_aux) > 0:
            min = self.metricsConstruction[servers_aux[0]][metric]["value"]
            node_min = self.metricsConstruction[servers_aux[0]][metric]["node"]
            servers_aux.pop(0)


        for server in servers_aux:
            metric_val = self.metricsConstruction[server][metric]["value"]
            if metric_val < min:
                min = metric_val
                node_min = self.metricsConstruction[server][metric]["node"]



        return node_min

    # por testar
    def updateNodeByGroup(self, group):
        """ self.metricsGroup = { group : { metric : node } }"""
        servers = self.groups[group]
        for metric in self.metrics:
            node_min = self.getMinNode(servers, metric)
            #inicializar metricsGroup
            if group not in self.metricsGroup.keys():
                self.metricsGroup[group] = {}

            self.metricsGroup[group][metric] = node_min
