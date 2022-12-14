import socket
import pickle
import time
import threading
from datetime import datetime
import sys
from .RtpPacket import RtpPacket
from .ProtocolPacket import ProtocolPacket
import copy


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
        self.activeClientsByNode = {}
        self.metricsGroup = {}
        self.lock = threading.Lock()
        self.metrics = ["rtt", "saltos"]
        self.entryPoint = False
        self.rootNode = False
        self.nodeName = ""
        self.nodeAddress = ""
        self.curEpoch = -1
        self.rtpSocket = socket.socket(type=socket.SOCK_DGRAM)

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
                client_socket.connect(
                    (self.bootstrapperIP, self.bootstrapperPort))
                # print("let's send alive message!")
                protocolPacket = ProtocolPacket("1", "")
                client_socket.send(pickle.dumps(protocolPacket))
            except Exception as e:
                print("Estou aqui AliveMessage")
            finally:
                client_socket.close()

    def opcode_3_handler(self, protocolPacket):
        print("opcode 3!")
        print(protocolPacket.data)
        print("Nodo ", protocolPacket.data["nodo"], " está desativo!")
        if protocolPacket.data["nodo"] in self.aliveNeighbours.keys():
            self.aliveNeighbours.pop(protocolPacket.data["nodo"])
        print("Active nodes update ----------------------------")
        print(self.aliveNeighbours)

    def opcode_4_handler(self, protocolPacket):
        # print("opcode 4!")
        # print("Nodo ", str(protocolPacket.data["nodo"]), " está ativo!")
        self.aliveNeighbours[str(protocolPacket.data["nodo"])
                             ] = protocolPacket.data["interfaces"]

        print("Active nodes update ----------------------------")
        print(self.aliveNeighbours)

    def opcode_5_handler(self, protocolPacket, address):

        # update metric from address node
        neighboorName = self.getNeighboorNameByAddress(address)
        metricsConstruction = {}
        metricsConstruction["saltos"] = protocolPacket.data["saltos"]
        metricsConstruction["tempo"] = datetime.now() - \
            protocolPacket.data["tempo"]
        self.metricsConstruction[neighboorName] = metricsConstruction

        # send probe packets to neighboors except address node
        for activeNeighboor in self.aliveNeighbours:
            if activeNeighboor != neighboorName:
                try:
                    client_socket = socket.socket()
                    # select a random interface from the active neighboor to send the message
                    # here what is relevant is to send the information to the node itself, no matter the interface.
                    client_socket.connect(
                        (self.aliveNeighbours[activeNeighboor][0]["ip"], 20003))
                    data = {}
                    data["saltos"] = protocolPacket.data["saltos"] + 1
                    data["tempo"] = protocolPacket.data["tempo"]
                    protocolPacket = ProtocolPacket("5", data)
                    client_socket.send(pickle.dumps(protocolPacket))
                except Exception as e:
                    print("Estou aqui 5")
                finally:
                    client_socket.close()

    def opcode_6_handler(self, protocolPacket):
        """I'm a root node and need to start a flood to update metrics to servers im rooting"""
        print("Received a flood metrics request")
        data = protocolPacket.data
        self.rootNode = True
        servers = data["servidores"]
        print(servers)
        epoch = data["epoch"]
        group_info = data["group_info"]

        self.updateGroups(group_info)

        for aliveNeighbour in self.aliveNeighbours:
            try:
                client_socket = socket.socket()
                client_socket.settimeout(1)
                #print("Alive neigbours ip " + self.aliveNeighbours[aliveNeighbour][0]["ip"])
                client_socket.connect(
                    (self.aliveNeighbours[aliveNeighbour][0]["ip"], 20003))
                data = {}
                data_servers = {}
                # for now this will be considered as an approximate metric of
                # time to the servers although it should be updated to a round trip
                # ping pong request to the servers
                for server in servers:
                    data_servers[server] = {"saltos": 0, "rtt": datetime.now()}

                data["servers"] = data_servers
                data["visited"] = [self.nodeName]
                data["epoch"] = epoch
                data["group_info"] = self.groups
                self.curEpoch = epoch

                for server, server_info in data_servers.items():
                    rtt_updated_dic = {"value": datetime.now(
                    ) - server_info["rtt"], "node": self.nodeName, "epoch": epoch}
                    saltos_updated_dic = {
                        "value": 0, "node": self.nodeName, "epoch": epoch}
                    if server not in self.metricsConstruction.keys():
                        self.metricsConstruction[server] = {
                            "saltos": {}, "rtt": {}}

                    self.metricsConstruction[server]["rtt"] = rtt_updated_dic
                    self.metricsConstruction[server]["saltos"] = saltos_updated_dic

                protocolPacket = ProtocolPacket("7", data)
                client_socket.send(pickle.dumps(protocolPacket))
            except Exception as e:
                print("Estou aqui 6")
            finally:
                client_socket.close()

    def updateGroups(self, group_info):
        #print("GROUP_INFO: " + str(group_info))
        #print("SELF.GROUP: " + str(self.groups))
        for group in group_info:
            #print("GROUP ITERATION: " + str(group_info[group]))
            if group not in self.groups.keys():
                self.groups[group] = group_info[group]
            else:
                for server in group_info[group]:
                    if server not in self.groups[group]:
                        self.groups[group].append(server)

        print("UPDATED SELF.GROUPS: " + str(self.groups))
    
    def opcode_7_handler(self, protocolPacket, address):
        """I'm an overlay layer and need to update my metrics and continue to flood"""
        neighbourName = self.getNeighboorNameByAddress(address)

        data = protocolPacket.data
        data_servers = data["servers"]
        visited = data["visited"]
        epoch = data["epoch"]
        group_info = data["group_info"]
        self.curEpoch = epoch

        old_group_metrics = copy.deepcopy(self.metricsGroup)
        print("OUTDATED METRICS" + str(self.metricsGroup))
        # update my own server metrics
        for server, server_info in data_servers.items():
            server_info = self.updateMetricsByServer(
                server, server_info, address, epoch)

        self.updateGroups(group_info)

        for group in self.groups:
            self.updateNodeByGroup(group)

        new_group_metrics = self.metricsGroup.copy()

        # Send to the above nodes that I no longer need some connections or request new connections based on active groups.
        # Check all the groups that have at least one client using them and request to the new best node, and cut to the previous node

        #print("UPDATED METRICS" + str(self.metricsConstruction))

        print("UPDATED METRICS GROUP" + str(self.metricsGroup))
        print("EPOCH " + str(epoch))

        if self.anyClientActive():
            for group_for in old_group_metrics:
                for metric_for in old_group_metrics[group_for]:
                    if self.affected(metric_for, group_for):
                        self.sendChangesMessages(old_group_metrics, new_group_metrics, metric_for, group_for)

        iteration_neigh = self.aliveNeighbours.copy()

        for alive in iteration_neigh:
            if alive != neighbourName and alive not in visited:
                visited.append(self.nodeName)
                data["visited"] = visited
                client_socket = socket.socket()
                client_socket.settimeout(1)
                try:
                    client_socket.connect(
                        (self.aliveNeighbours[alive][0]["ip"], 20003))
                    protocolPacket = ProtocolPacket("7", data)
                    client_socket.send(pickle.dumps(protocolPacket))
                except Exception as e:
                    print("Estou aqui 7")
                finally:
                    client_socket.close()

    def affected(self, metric, group):
        for node in self.activeClientsByNode:
            for metric_for in self.activeClientsByNode[node]:
                if group in self.activeClientsByNode[node][metric_for].keys() and metric == metric_for:
                    return True

        return False
                
    def anyClientActive(self):
        print("ACTIVE CLIENTS: " + str(self.activeClientsByNode))
        r = []
        for node in self.activeClientsByNode.keys():
            for metric in self.activeClientsByNode[node].keys():
                for group in self.activeClientsByNode[node][metric].keys():
                    if self.activeClientsByNode[node][metric][group] > 0:
                        return True

        return False

    def sendChangesMessages(self, old, new, metric, group):
        # Lembrar que no futuro se houver adição de grupos dinâmicos tenho que
        # garantir que self.groups é atualizado
        # iterate through groups
        print("OLD: " + str(old))
        print("NEW: " + str(new))

        if len(old) == 0:
            return

        # there was a change, need to send messages
        old_node = old[group][metric]
        new_node = new[group][metric]
        if old_node != new_node:
            # Send protocol message number 8 to indicate I want
            # to listen to a new stream
            client_socket = socket.socket()
            client_socket.settimeout(1)
            try:
                client_socket.connect(
                    (self.aliveNeighbours[new_node][0]["ip"], 20003))
                data = {}
                data["group"] = group
                data["metric"] = metric
                data["action"] = "START"
                protocolPacket = ProtocolPacket("9", data)
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
                client_socket.connect(
                    (self.aliveNeighbours[old_node][0]["ip"], 20003))
                data = {}
                data["group"] = group
                data["metric"] = metric
                data["action"] = "STOP"
                protocolPacket = ProtocolPacket("9", data)
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

    def updateMetricsByServer(self, server, server_info, address, epoch):
        """ server layout : 's1' ex. server_info : { 'saltos': 0, 'rtt' : time.now()}"""
        """ self.metricsConstruction layout :{ 's2' : {'saltos' : {'value' : 2, 'node' : 'n1', 'epoch' : 3}, 'rtt' { 'value' : datetime.now(), 'node' : 'n2', 'epoch' : 2}}} """

        # send to neighbours

        neighbourName = self.getNeighboorNameByAddress(address)
        print("NEIGHBOUR NAME " + neighbourName)
        metrics_info = self.metricsConstruction
        saltos_arg = server_info["saltos"]
        rtt_arg = server_info["rtt"]

        rtt_new = datetime.now() - rtt_arg
        saltos_new = saltos_arg + 1

        # for all metrics check if there is a better metric
        # TODO Há o problema em que tenho que atualizar a métrica para cada iteração
        # Posso criar uma noção de épocas e comparar épocas de métricas.
        # Assume-se a inicialização de estruturas

        rtt_updated_dic = {"value": rtt_new,
                           "node": neighbourName, "epoch": epoch}
        saltos_updated_dic = {"value": saltos_new,
                              "node": neighbourName, "epoch": epoch}
        # first update outdated metrics
        try:
            saltos_present = metrics_info[server]["saltos"]["value"]
            rtt_present = metrics_info[server]["rtt"]["value"]

            if metrics_info[server]["rtt"]["epoch"] + 1 < epoch or rtt_new < rtt_present:
                metrics_info[server]["rtt"] = rtt_updated_dic

            if metrics_info[server]["saltos"]["epoch"] + 1 < epoch or saltos_new < saltos_present:
                metrics_info[server]["saltos"] = saltos_updated_dic
        except:
            # Server did not exist
            metrics_info[server] = {"rtt": {}, "saltos": {}}
            metrics_info[server]["rtt"] = rtt_updated_dic
            metrics_info[server]["saltos"] = saltos_updated_dic

        server_info["saltos"] += 1
        # server_info["rtt"] mantains the same since the goal is to have the original timestamp of the root node, for now.

        return server_info

    def opcode_8_handler(self, protocolPacket, address):
        """I'm a overlay layer node and received a message to create or a remove  connection with you"""
        # self.activeClientsByNode add mais um
        node = self.getNeighboorNameByAddress(address)

        data = protocolPacket.data
        group = data["group"]
        metric = data["metric"]
        action = data["action"]

        old_active = self.activeClientsByNode
        self.checkAndInitActiveClients(node, metric, group)

        if action == "STOP":
            cur = max(0, cur - 1)
        elif action == "START":
            cur += 1
        else:
            pass

        if cur != 0:
            self.activeClientsByNode[node][metric][group] = cur
        else:
            self.activeClientsByNode.pop(node)

        print("ACTIVE CLIENTS : " + str(self.activeClientsByNode))

        if len(self.activeClientsByNode) == 0:
            packet = ProtocolPacket("2", "")
            socket_server = socket.socket()
            socket_server.settimeout(1)

            for server in self.servers:
                server_ip = self.servers[server]["ip"]
                try:
                    socket_server.connect((server_ip, 20004))
                    socket_server.send(pickle.dumps(packet))
                except:
                    print("Estou aqui 8")
                finally:
                    socket_server.close()
        elif len(old_active) == 0 and len(self.activeClientsByNode) != 0:
            packet = ProtocolPacket("1", "")
            socket_server = socket.socket()
            socket_server.settimeout(1)

            for server in self.servers:
                server_ip = self.servers[server]["ip"]
                try:
                    socket_server.connect((server_ip, 20004))
                    socket_server.send(pickle.dumps(packet))
                except:
                    print("Estou aqui 8")
                finally:
                    socket_server.close()

    def opcode_9_handler(self, protocolPacket, address):
        """ I'm a overlay node and a client decided to stopped/requested to watch a stream.
        Need to tell my best neighbour for each metric (way to the root) """
        # make functions to check init and init
        # make function to update active interfaces

        node = self.getNeighboorNameByAddress(address)
        if node == None and self.entryPoint == True:
            node = self.getClient(address)

        print("NODE IN 9: " + str(node))
        data = protocolPacket.data
        group = data["group"]
        metric = data["metric"]
        action = data["action"]
        old_active = copy.deepcopy(self.activeClientsByNode)
        self.checkAndInitActiveClients(node, metric, group)

        cur = self.activeClientsByNode[node][metric][group]
        if action == "STOP":
            print("I'M GOING TO STOP FOR " + node)
            cur = max(0, cur - 1)
        elif action == "START":
            print("I'M GOING TO START FOR " + node)
            cur += 1
        else:
            pass

        if cur != 0:
            self.activeClientsByNode[node][metric][group] = cur
        else:
            self.activeClientsByNode.pop(node)
         

        print("ACTIVE CLIENTS : " + str(self.activeClientsByNode))

        if len(self.metricsGroup) != 0:
            parent_node = self.metricsGroup[group][metric]
            if parent_node != self.nodeName:
                client_socket = socket.socket()
                client_socket.settimeout(1)

                try:
                    client_socket.connect(
                        (self.aliveNeighbours[parent_node][0]["ip"], 20003))
                    protocolPacket = ProtocolPacket("9", data)
                    client_socket.send(pickle.dumps(protocolPacket))
                except Exception as e:
                    print("Estou aqui 9")
                finally:
                    client_socket.close()
            else:
                if len(self.activeClientsByNode) == 0:
                    packet = ProtocolPacket("2", "")
                    socket_server = socket.socket()
                    socket_server.settimeout(1)

                    for server in self.servers:
                        server_ip = self.servers[server]["ip"]
                        try:
                            socket_server.connect((server_ip, 20004))
                            socket_server.send(pickle.dumps(packet))
                        except:
                            print("Estou aqui 8")
                        finally:
                            socket_server.close()
                elif len(old_active) == 0 and len(self.activeClientsByNode) != 0:
                    print("> Como sou o root node, enviarei para o servidor o pedido da stream")
                    packet = ProtocolPacket("1", "")
                    socket_server = socket.socket()
                    socket_server.settimeout(1)

                    for server in self.servers:
                        #print("ESTOU AQUI")
                        server_ip = self.servers[server]["ip"]
                        try:
                            socket_server.connect((server_ip, 20004))
                            socket_server.send(pickle.dumps(packet))
                        except:
                            print("(!)Exceção no momento de conexão do root node com o servidor")
                        finally:
                            socket_server.close()

    def sendRequestPacket(self, node, data, opcode):
        client_socket = socket.socket()
        client_socket.settimeout(1)

        try:
            client_socket.connect((self.aliveNeighbours[node][0]["ip"], 20003))
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
        self.clientNo += 1
        print("IP :" + address)
        self.aliveClients[client_name] = address
        print(self.aliveClients)

    def opcode_11_handler(self, protocolPacket, address):
        """I'm an entryPoint and I'll remove a client"""
        """If I get no clients I'll no longer be an entryPoint"""

        if self.entryPoint:
            client = self.getClient(address)

            if client != None:
                # remove client from activeInterfaces
                if client in self.activeClientsByNode.keys():
                    data = {}
                    data["action"] = "STOP"
                    # If the client didn't pause we will
                    # Will send the stop request for my parent nodes
                    for metric in self.activeClientsByNode[client]:
                        data["metric"] = metric
                        for group in self.activeClientsByNode[client][metric]:
                            data["group"] = group
                            parent_node = self.metricsGroup[group][metric]
                            self.sendRequestPacket(parent_node, data, "9")

                    self.activeClientsByNode.pop(client)

                # remove client from client with a session
                self.aliveClients.pop(client)
                if len(self.aliveClients) == 0:
                    self.entryPoint = False

    def opcode_12_handler(self, protocolPacket):
        """ I'm a rootNode and received the information that
        I have a new server"""
        data = protocolPacket.data
        server_name = data["server_name"]
        server_ip = data["server_ip"]

        self.servers[server_name] = {"ip": server_ip}

    def opcode_13_handler(self, protocolPacket):
        """ I'm a rootNode and received the information that
        a server of mine has decided to leave the network"""
        data = protocolPacket.data
        server_name = data["server_name"]

        if server_name in self.servers.keys():
            del self.servers[server_name]

    def getClient(self, address):
        for client, ip in self.aliveClients.items():
            if ip == address:
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
    def demultiplexer(self, conn, address):

        try:
            data = conn.recv(1024)
            # parser data request into a protocolPacket (opcode + data)
            self.lock.acquire()
            protocolPacket = pickle.loads(data)

            # invoke an action according to the opcode
            if protocolPacket.opcode == '3':
                self.opcode_3_handler(protocolPacket=protocolPacket)
            elif protocolPacket.opcode == '4':
                self.opcode_4_handler(protocolPacket=protocolPacket)
            elif protocolPacket.opcode == '5':
                self.opcode_5_handler(
                    protocolPacket=protocolPacket, address=address[0])
            elif protocolPacket.opcode == '6':
                self.opcode_6_handler(protocolPacket=protocolPacket)
            elif protocolPacket.opcode == '7':
                self.opcode_7_handler(
                    protocolPacket=protocolPacket, address=address[0])
            elif protocolPacket.opcode == '8':
                self.opcode_8_handler(
                    protocolPacket=protocolPacket, address=address[0])
            elif protocolPacket.opcode == '9':
                self.opcode_9_handler(
                    protocolPacket=protocolPacket, address=address[0])
            elif protocolPacket.opcode == '10':
                self.opcode_10_handler(
                    protocolPacket=protocolPacket, address=address[0])
            elif protocolPacket.opcode == '11':
                self.opcode_11_handler(protocolPacket, address[0])
            elif protocolPacket.opcode == '12':
                self.opcode_12_handler(protocolPacket)
            else:
                print("opcode unknown")
        except EOFError:
            print("EOF error")
        except socket.error:
            conn.close()
        except Exception as e:
            print(str(e))
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
            client_socket.connect((self.bootstrapperIP, self.bootstrapperPort))

            # ask for info of alive Neighbours
            protocolPacket = ProtocolPacket("0", "")
            print("sent info")
            client_socket.send(pickle.dumps(protocolPacket))
            # recieve info
            data = client_socket.recv(1024)
            protocolPacket = pickle.loads(data)

            print("Received from server my current active neighboors: ",
                  protocolPacket.data)
            for node in protocolPacket.data:
                self.aliveNeighbours[node["nodo"]] = node["interfaces"]
            # ask for info of current servers and current groups

            client_socket.close()
            client_socket = socket.socket()
            client_socket.connect((self.bootstrapperIP, self.bootstrapperPort))

            protocolPacket = ProtocolPacket("2", "")
            client_socket.send(pickle.dumps(protocolPacket))
            protocolPacket = client_socket.recv(1024)
            data = pickle.loads(protocolPacket).data

            # init server structure
            print(data)
            print("Received from server the initial server and group configuration")
            self.servers = data["server_info"]
            print(data["server_info"])
            # init group structure
            # Structure self.groups = { group_no : ["s3", "s1", "s4"] }
            self.groups = data["group_info"]
            print(data["group_info"])

            self.nodeName = data["node_name"]
            self.nodeAddress = data["node_address"]

            # init metricsConstructions with max values
            for server in self.servers.keys():
                self.metricsConstruction[server] = {"saltos": {"value": sys.maxsize, "node": self.nodeName, "epoch": 0}, "rtt": {
                    "value": datetime.now() - datetime(1970, 1, 1), "node": self.nodeName, "epoch": 0}}

            # Structure helf.activeClientsByNode = { neighbour_node : { metric : {group_no : count } }}
            # for node in self.aliveNeighbours:
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
            server_socket.bind(("0.0.0.0", 20003))
            server_socket.listen(2)

            while (True):
                print("wait server to send neighboor updates")
                conn, address = server_socket.accept()
                self.demultiplexer(conn, address)
        finally:
            server_socket.close()

    # description: activate getNeighboors and  aliveMessage thread
    def start(self):

        serviceThread = threading.Thread(target=self.service)
        serviceThread.start()

        aliveMessageThread = threading.Thread(target=self.aliveMessage)
        aliveMessageThread.start()

        forwardThread = threading.Thread(target=self.forward)
        forwardThread.start()

    def forward(self):
        print("Comecei a thread do forwarding!")
        self.rtpSocket.bind(("0.0.0.0", 20005))
        while True:
            try:
                data = self.rtpSocket.recv(20005)
                if data:
                    print("Recebido pacote da stream para fazer forwarding ...")
                    rtpPacket = RtpPacket()
                    rtpPacket.decode(data)

                    payload = rtpPacket.getPayload()

                    packet = pickle.loads(payload)
                    group = packet.opcode
                    file_data = packet.data

                    # get active neigh with group
                    active_nodes = self.getActiveNodesByGroup(group)

                    print("Active nodes to forwarding: ",active_nodes)

                    # for neigh group send packet
                    for node in active_nodes:
                        print("Realizando envio do pacote da stream para os vizinhos ativos ...")
                        try:
                            node_ip = self.aliveNeighbours[node][0]["ip"]
                            print("IP do vizinho ativo: ",node_ip)
                            self.rtpSocket.sendto(
                                rtpPacket.getPacket(), (node_ip, 20005))
                        except:
                            print("Vizinho ativo é o cliente final e será tratado a seguir!")

                    if self.entryPoint == True:
                        print("Como sou o entry point dos clientes, devo mandá-los a stream ..")
                        for client in self.aliveClients:
                            client_ip = self.aliveClients[client]
                            self.rtpSocket.sendto(
                                rtpPacket.getPacket(), (client_ip, 20005))
            except:
                print("Estou aqui Forward")

    # routing functions
    def getClosestNeighbour(self, group, metric):
        servers = self.groups[group]
        node_min = self.getMinNode(servers, metric)
        return node_min

    # Por testar
    def getMinNode(self, servers, metric):
        servers_aux = servers.copy()
        min = None
        node_min = None

        for server in servers_aux:
            metric_val = self.metricsConstruction[server][metric]["value"]
            metric_epoch = self.metricsConstruction[server][metric]["epoch"]
            metric_node = self.metricsConstruction[server][metric]["node"]

            if (min == None or metric_val < min) and self.curEpoch - metric_epoch <= 1 :
                min = metric_val
                node_min = metric_node

        return node_min

    # por testar
    def updateNodeByGroup(self, group):
        """ self.metricsGroup = { group : { metric : node } }"""
        servers = self.groups[group]
        print("SERVERS IN UPDATE NODE: " + str(servers))
        for metric in self.metrics:
            node_min = self.getMinNode(servers, metric)
            # inicializar metricsGroup
            if group not in self.metricsGroup.keys():
                self.metricsGroup[group] = {}

            self.metricsGroup[group][metric] = node_min

    def getActiveNodesByGroup(self, group):
        print(self.activeClientsByNode)
        res = []
        for node in self.activeClientsByNode.keys():
            for metric in self.activeClientsByNode[node].keys():
                for group_no in self.activeClientsByNode[node][metric].keys():
                    if str(group_no) == str(group):
                        res.append(node)

        return res
