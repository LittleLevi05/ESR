import json

class ConfigTopology:
    def __init__(self, configFile):
        f = open(configFile)
        self.configFile = json.load(f)
        self.aliveNodes = {}

    def getNodeNameByAddress(self,address):
        for nodo in self.configFile["topologia"]:
            for interface in nodo["interfaces"]:
                if interface["ip"] == address:
                    return nodo["nodo"]            

    def getVizinhosInterfaces(self,vizinhos):
        vizinhosComInterfaces = []

        for vizinho in vizinhos:
            vizinhosComInterface = {}
            vizinhosComInterface["nodo"] = vizinho["nodo"]
            interfaceDosVizinhos = []
            for nodo in self.configFile["topologia"]:
                if nodo["nodo"] == vizinho["nodo"]:
                    interfaceDosVizinhos = nodo["interfaces"]
            vizinhosComInterface["interfaces"] = interfaceDosVizinhos
            vizinhosComInterfaces.append(vizinhosComInterface)

        return vizinhosComInterfaces

    def getVizinhos(self,nodeName):
        for nodo in self.configFile["topologia"]:
            if nodo["nodo"] == nodeName:
                return self.getVizinhosInterfaces(nodo["vizinhos"])

    def getInterfaces(self,nodeName):
        for nodo in self.configFile["topologia"]:
            if nodo["nodo"] == nodeName:
                return nodo["interfaces"]


    def getRandomInterface(self, nodeName):
        interfaces = self.getInterfaces(nodeName)
        return interfaces[0]["ip"]

    def checkIfNodeIsAlive(self,node):
        if node in self.aliveNodes:
            return True
        else:
            return False
    def getServersNamesByGroup(self, groupNumber):
        servers = []
        for group in self.configFile["grupos"]:
            if group["grupo"] == groupNumber:
                for server in group["servidores"]:
                    servers.append(server["servidor"])

        return servers

    def getServerAddresByName(self, serverName):
        for server in self.configFile["servidores"]:
            if server["servidor"] == serverName:
                return server["ip"]

    def getGroupsByFilename(self, fileName):
        groups = []
        for group in self.configFile["grupos"]:
            if group["ficheiro"] == fileName:
                groups.append(group["group"])

        return groups

    def getRootNodesAndServers(self):
        rootNodes = {}
        #print(self.configFile["servidores"])
        for server in self.configFile["servidores"]:
            if server["rootNode"] in rootNodes.keys():
                rootNodes[server["rootNode"]].append(server["servidor"])
            else:
                rootNodes[server["rootNode"]] = [server["servidor"]]

        #print(rootNodes)
        return rootNodes

    def getServers(self):
        servers = {}
        for server in self.configFile["servidores"]:
            servers[server["servidor"]] = {"ip" : server["ip"]}

        return servers

    def getGroups(self):
        """ Return group_name: [ list of servers that supply the group ] """
        groups = {}
        for group in self.configFile["grupos"]:
            groups[group["grupo"]] = self.getServersNamesByGroup(group["grupo"])

        return groups

    def addServer(self, address, name, rootNode):
        { "servidor" : name, "ip" : address, "rootNode" : rootNode}
        self.configFile["servidores"].append()


    def delServer(self, address):
        i = 0
        found = False
        for server in self.configFile["servidores"]:
            if server["ip"] == address:
                found = True
                break
            i += 1

        if found == True:
            server = self.configFile["servidores"].pop(i)
            return server

        return None


    def addServerToGroup(self, name, group):
        for group in self.configFile["grupos"]:
            if group["grupo"] == group:
                group["servidores"].append({"servidor" : name})
                break

    def delServerFromGroups(self, name):
        for group in self.configFile["grupos"]:
            groups_servers = group["servidores"].copy()
            for server in groups_servers:
                if server["servidor"] == name:
                    group["servidores"].remove({"servidor" : name })
