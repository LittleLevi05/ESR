from ensurepip import bootstrap
#from server.server import Server
#from client.client import Client 
from topology.BootstrapperServer import BootstrapperServer
from topology.BootstrapperClient import BootstrapperClient
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

args, unknown = parser.parse_known_args()

# caso o sistema for o bootstrapper
if args.configFile: 
    bootstrapperServer = BootstrapperServer(args.ipBootstrapper,20002,args.configFile)
    threadBootstrapperServer = threading.Thread(target = bootstrapperServer.start)
    print("Iniciando servidor bootstrapper!")
    threadBootstrapperServer.start()

# caso o sistema não for o bootstrapper
if not args.configFile:
    bootstrapperClient = BootstrapperClient(args.ipBootstrapper,20002)
    threadBootstrapperClient = threading.Thread(target = bootstrapperClient.start)
    print("Iniciando cliente bootstrapper!")
    threadBootstrapperClient.start()

#server = Server(args.myIp, 20001)
#client = Client(args.ipBootstrapper, 20001)

#threadServer = threading.Thread(target = server.start)
#threadClient = threading.Thread(target = client.start)

#threadServer.start()
#threadClient.start()

#threadServer.join()
#threadClient.join()
