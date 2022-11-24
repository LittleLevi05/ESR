import sys, socket

from ServerWorker import ServerWorker

import argparse


parser = argparse.ArgumentParser(
    prog = 'Server',
    description = 'TP2 ESR',
    epilog = 'Made by Henrique and José'
)

parser.add_argument('portServer', type=int, help="Port of the multimedia content server")


args, unknown = parser.parse_known_args()


class Server:


	def main(self):
		try:
			SERVER_PORT = args.portServer
		except:
			print("[Usage: Server.py Server_port]\n")
		rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		rtspSocket.bind(('', SERVER_PORT))
		rtspSocket.listen(5)

		# Receive client info (address,port) through RTSP/TCP session
		while True:
			clientInfo = {}
			clientInfo['rtspSocket'] = rtspSocket.accept()
			ServerWorker(clientInfo).run()

if __name__ == "__main__":
	(Server()).main()


