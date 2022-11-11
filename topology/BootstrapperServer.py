import socket
from .ConfigTopology import ConfigTopology
from .ProtocolPacket import ProtocolPacket
import pickle

class BootstrapperServer:
    def __init__(self, ip, port, configFile):
        self.ip = ip
        self.port = port
        self.configTopology = ConfigTopology(configFile)

    def demultiplexer(self,conn,address):

        data = conn.recv(1024)
        protocolPacket = pickle.loads(data)
        
        if protocolPacket.opcode == '0': 
            vizinhos = self.configTopology.getVizinhos(address[0])
            protocolPacket = ProtocolPacket("1",vizinhos)
            conn.send(pickle.dumps(protocolPacket))
        elif protocolPacket.opcode == '1':
            print("Opcode 1")
        else:
            print("Opcode error")

    def start(self):
        server_socket = socket.socket() 
        server_socket.bind((self.ip,self.port))
        server_socket.listen(2) # Número de clientes que o servidor atende simultâneamente

        try:
            while(True):
                conn, address = server_socket.accept()
                print("Recebido pacote do endereço: " + str(address))
                self.demultiplexer(conn,address)
        except:
            server_socket.close()  
        finally:
            server_socket.close()

          

            