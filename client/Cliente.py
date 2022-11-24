import sys
from tkinter import Tk
from Client import Client
import argparse

parser = argparse.ArgumentParser(
    prog = 'Cliente',
    description = 'TP2 ESR',
    epilog = 'Made by Henrique and José'
)

parser.add_argument('ipServer', type=str, help="IP of the multimedia content server")
parser.add_argument('portServer', type=int, help="Port of the multimedia content server")
parser.add_argument('rtpPort', type=int, help="Port of the multimedia server that is running")

args, unknown = parser.parse_known_args()


if __name__ == "__main__":
	try:
		addr = args.ipServer
		port = args.portServer
		rtpPort = args.rtpPort
	except:
		print("[Usage: Cliente.py]\n")

	root = Tk()

	# Create a new client
	app = Client(root, addr, port, rtpPort, "movie.Mjpeg")
	app.master.title("Cliente Exemplo")
	root.mainloop()

