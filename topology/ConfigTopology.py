import json

class ConfigTopology:
    def __init__(self, configFile):
        f = open(configFile)
        self.configFile = json.load(f)

    def getVizinhos(self,address):
        for nodo in self.configFile["topologia"]:
            if nodo["ip"] == address:
                return nodo["vizinhos"]
        

            