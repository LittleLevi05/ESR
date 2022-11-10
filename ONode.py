from ensurepip import bootstrap
from server.server import Server
from client.client import Client 
from topology.Bootstrapper import Bootstrapper
import threading
import argparse

# Arguments 
configFile = ''
ipBootstraper = ''
myIp = ''

# Parser
parser = argparse.ArgumentParser(
    prog = 'ONode',
    description = 'TP2 ESR',
    epilog = 'Made by Henrique and José'
)

parser.add_argument('-cf',help="Define the config file for the bootstraper node",dest='configFile')
parser.add_argument('ipBootstrapper',type=str,help="IP of bootstraper node")
parser.add_argument('myIp',type=str,help="IP of current node")

args, unknown = parser.parse_known_args()

server = Server(args.myIp, 20001)
client = Client(args.ipBootstrapper, 20001)

if args.configFile:
    bootstrapper = Bootstrapper(args.ipBootstrapper,20002,configFile)
    threadBootstrapper = threading.Thread(target = bootstrapper.start)
    threadBootstrapper.start()

threadServer = threading.Thread(target = server.start)
threadClient = threading.Thread(target = client.start)

threadServer.start()
threadClient.start()

threadServer.join()
threadClient.join()
