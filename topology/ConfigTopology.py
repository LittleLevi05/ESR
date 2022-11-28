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
                rootNodes[server["rootNode"]].append({"servidor" : server["servidor"], "ip": server["ip"]})
            else:
                rootNodes[server["rootNode"]] = [{"servidor" : server["servidor"], "ip" : server["ip"]}]

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
