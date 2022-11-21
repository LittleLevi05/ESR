import sys
from tkinter import Tk
from Client import Client

if __name__ == "__main__":
	try:
		addr = '127.0.0.1'
		port = 25000
	except:
		print("[Usage: Cliente.py]\n")

	root = Tk()

	# Create a new client
	app = Client(root, addr, port, 23500, "movie.Mjpeg")
	app.master.title("Cliente Exemplo")
	root.mainloop()

