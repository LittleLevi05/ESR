import sys
import socket

from ServerWorker import ServerWorker

import argparse
import pickle

sys.path.append("..")
from topology.ProtocolPacket import ProtocolPacket


parser = argparse.ArgumentParser(
    prog='Server',
    description='TP2 ESR',
    epilog='Made by Henrique and José'
)

parser.add_argument('--ipBoot', '-i', type=str,
                    help="IP of the multimedia content server", required=False)
parser.add_argument('--portBoot', '-p', type=int,
                    help="Port of the multimedia content server", required=False)
parser.add_argument('--rtpPort', '-r', type=int,
                    help="Port of the multimedia server that is running", required=False)
parser.add_argument('--ipRootNode', '-n', type=str,
                    help="Port of the multimedia server that is running", required=False)
parser.add_argument('--filename', '-f', type=str,
                    help="Port of the multimedia server that is running", required=True)


args, unknown = parser.parse_known_args()


class Server:
    def __init__(self):
        self.ipBoot = "127.000.001"
        self.portBoot = 20002
        self.rtpPort = 20005
        self.ipRootNode = "127.000.001"
        self.group = 1
        self.filename = ""

    def main(self):
        try:
            if args.ipBoot != None:
                self.ipBoot = args.ipBoot
            if args.portBoot != None:
                self.portBoot = args.portBoot
            if args.rtpPort != None:
                self.rtpPort = args.rtpPort
            if args.ipRootNode != None:
                self.ipRootNode = args.ipRootNode
            if args.filename != None:
                self.filename = args.filename
        except:
            print("[Usage: Server.py Server_port]\n")

        # Enviar pedidos ao bootstrapper

        boot_socket = socket.socket()
        boot_socket.settimeout(1)

        # ask for group
        try:
            boot_socket.connect((self.ipBoot, self.portBoot))
            data = {}
            data["filename"] = self.filename
            packet = ProtocolPacket("5", data)
            boot_socket.send(pickle.dumps(packet))
            data = boot_socket.recv(1024)
            packet = pickle.loads(data)
            self.group = packet.data["group"]
        except:
            print("Estou aqui Pedir grupo")
        finally:
            boot_socket.close()

        # inform that I am joining the network
        boot_socket = socket.socket()
        boot_socket.settimeout(1)
        try:
            boot_socket.connect((self.ipBoot, self.portBoot))
            data = {}
            data["group"] = self.group
            data["rootNode"] = self.ipRootNode

            packet = ProtocolPacket("3", data)

            boot_socket.send(pickle.dumps(packet))
        except:
            print("Estou aqui para Entrar num grupo")
        finally:
            boot_socket.close()

        print("ESTOU AQUI")

        clientInfo = {}
        clientInfo['rtpPort'] = self.rtpPort
        clientInfo['address'] = self.ipRootNode
        clientInfo['group'] = self.group
        print("I'm here")
        ServerWorker(clientInfo, self.filename).run()



if __name__ == "__main__":
    server = Server()
    server.main()
