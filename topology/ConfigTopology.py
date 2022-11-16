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

    def checkIfNodeIsAlive(self,node):
        if node in self.aliveNodes:
            return True
        else:
            return False
        

            