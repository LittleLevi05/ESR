import sys
from tkinter import Tk
from Client import Client
import argparse

parser = argparse.ArgumentParser(
    prog = 'Cliente',
    description = 'TP2 ESR',
    epilog = 'Made by Henrique and José'
)

parser.add_argument('--ipServer', '-i', type=str, help="IP of the multimedia content server", required=False)
parser.add_argument('--portServer', '-p', type=int, help="Port of the multimedia content server", required=False)
parser.add_argument('--rtpPort', '-r', type=int, help="Port of the multimedia server that is running", required=False)

args, unknown = parser.parse_known_args()

addr = "127.000.001"
port = 20003
rtpPort = 20005

if __name__ == "__main__":
        try:
                if args.ipServer != None:
                        addr = args.ipServer
                if args.portServer != None:
                        port = args.portServer
                if args.rtpPort != None:
                        rtpPort = args.rtpPort
        except:
                print("[Usage: Cliente.py]\n")

        root = Tk()

        print(addr)
        print(port)
        print(rtpPort)

        # Create a new client
        app = Client(root, addr, port, rtpPort, "movie.Mjpeg")
        app.master.title("Cliente Exemplo")
        root.mainloop()