from tkinter import *
import sys
import tkinter.messagebox
from PIL import Image, ImageTk
import socket, threading, sys, traceback, os
from ProtocolPacket import ProtocolPacket
import pickle

# append the path of the
# parent directory
sys.path.append("..")

from helpers import RtpPacket

CACHE_FILE_NAME = "cache-"
CACHE_FILE_EXT = ".jpg"

class Client:
	INIT = 0
	READY = 1
	PLAYING = 2
	state = INIT

	SETUP = 0
	PLAY = 1
	PAUSE = 2
	TEARDOWN = 3

	# Initiation..
	def __init__(self, master, serveraddr, serverport, rtpport, group):
		self.master = master
		self.master.protocol("WM_DELETE_WINDOW", self.handler)
		self.createWidgets()
		self.serverAddr = serveraddr
		self.serverPort = int(serverport)
		self.rtpPort = int(rtpport)
		self.rtspSeq = 0
		self.sessionId = 0
		self.requestSent = -1
		self.teardownAcked = 0
		#self.connectToServer()
		self.frameNbr = 0
		self.group = group

	def __create_request(self, method):
		request = method + " " + self.fileName + " " + "RTSP/1.0" + "\n"
		request += "Cseq: " + str(self.rtspSeq) + "\n"
		request += "Transport:" + " " + "RTP/AVP/UDP" + " " + "unicast" + " " + str(self.rtpPort) + "\n"
		return request

	def createWidgets(self):
		"""Build GUI."""

		self.setup = Button(self.master, width=20, padx=3, pady=3)
		self.setup["text"] = "Setup"
		self.setup["command"] = self.setupMovie
		self.setup.grid(row=1, column=0, padx=2, pady=2)

		# Create Play button		
		self.start = Button(self.master, width=20, padx=3, pady=3)
		self.start["text"] = "Play"
		self.start["command"] = self.playMovie
		self.start.grid(row=1, column=1, padx=2, pady=2)
		
		# Create Pause button			
		self.pause = Button(self.master, width=20, padx=3, pady=3)
		self.pause["text"] = "Pause"
		self.pause["command"] = self.pauseMovie
		self.pause.grid(row=1, column=2, padx=2, pady=2)

		self.teardown = Button(self.master, width=20, padx=3, pady=3)
		self.teardown["text"] = "Teardown"
		self.teardown["command"] =  self.exitClient
		self.teardown.grid(row=1, column=3, padx=2, pady=2)
		
		# Create a label to display the movie
		self.label = Label(self.master, height=40)
		self.label.grid(row=0, column=0, columnspan=4, sticky=W+E+N+S, padx=5, pady=5) 
	
	def setupMovie(self):
		"""Setup button handler."""
		if self.state == self.INIT:
			self.state = self.READY
			socket_server = socket.socket()
			socket_server.settimeout(1)
			try:
				socket_server.connect((self.serverAddr, self.serverPort))
				packet = ProtocolPacket("10", "")
				socket_server.send(pickle.dumps(packet))
			except:
				print("Estou aqui setupMovie")
			finally:
				socket_server.close()

	def exitClient(self):
		"""Teardown button handler."""
		socket_server = socket.socket()
		socket_server.settimeout(1)

		try:
			socket_server.connect((self.serverAddr, self.serverPort))
			packet = ProtocolPacket("11", "")
			socket_server.send(pickle.dumps(packet))
		except:
			print("Estou aqui exitClient")
		finally:
			socket_server.close()

		self.master.destroy() # Close the gui window
		os.remove(CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT) # Delete the cache image from video

	def pauseMovie(self):
		"""Pause button handler."""
		if self.state == self.PLAYING:
			print("Pause")
			#self.playEvent.set()
			self.state = self.READY
			self.sendRequest(self.PAUSE)

	def playMovie(self):
		"""Play button handler."""
		if self.state == self.READY:
			# Create a new thread to listen for RTP packets
			print("Play")
			#threading.Thread(target=self.listenRtp).start()
			#self.playEvent = threading.Event()
			#self.playEvent.clear()
			self.state = self.PLAYING
			self.sendRequest(self.PLAY)


	def sendRequest(self, type):
		socket_server = socket.socket()
		socket_server.settimeout(1)

		data = {}
		data["group"] = group
		data["metric"] = "rtt"
		if type == self.PLAY:
			data["action"] = "START"
		elif type == self.PAUSE:
			data["action"] = "STOP"
		try:
			socket_server.connect((self.serverAddr, self.serverPort))
			packet = ProtocolPacket("9", data)
			socket_server.send(pickle.dumps(packet))
		except:
			print("Estou aqui sendRequest")
		finally:
			socket_server.close()

	def listenRtp(self):
		"""Listen for RTP packets."""
		while True:
			try:
				data = self.rtpSocket.recv(20480)
				if data:
					rtpPacket = RtpPacket()
					rtpPacket.decode(data)
					
					currFrameNbr = rtpPacket.seqNum()
					print("Current Seq Num: " + str(currFrameNbr))
										
					if currFrameNbr > self.frameNbr: # Discard the late packet
						self.frameNbr = currFrameNbr
						self.updateMovie(self.writeFrame(rtpPacket.getPayload()))
			except:
				# Stop listening upon requesting PAUSE or TEARDOWN
				if self.playEvent.isSet(): 
					break
				
				# Upon receiving ACK for TEARDOWN request,
				# close the RTP socket
				if self.teardownAcked == 1:
					#self.rtpSocket.shutdown(socket.SHUT_RDWR)
					self.rtpSocket.close()
					break
					
	def writeFrame(self, data):
		"""Write the received frame to a temp image file. Return the image file."""
		cachename = CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT
		file = open(cachename, "wb")
		file.write(data)
		file.close()
		
		return cachename
	
	def updateMovie(self, imageFile):
		"""Update the image file as video frame in the GUI."""
		photo = ImageTk.PhotoImage(Image.open(imageFile))
		self.label.configure(image = photo, height=288) 
		self.label.image = photo
		
	def connectToServer(self):
		"""Connect to the Server. Start a new RTSP/TCP session."""
		self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		try:
			self.rtspSocket.connect((self.serverAddr, self.serverPort))
		except:
			tkinter.messagebox.showwarning('Connection Failed', 'Connection to \'%s\' failed.' %self.serverAddr)
	
	def sendRtspRequest(self, requestCode):
		"""Send RTSP request to the server."""	
		#-------------
		# TO COMPLETE
		#-------------
		
		# Setup request
		if requestCode == self.SETUP and self.state == self.INIT:
			threading.Thread(target=self.recvRtspReply).start()
			# Update RTSP sequence number.
			self.rtspSeq += 1
			# Write the RTSP request to be sent.
			request = self.__create_request("SETUP")
			# Keep track of the sent request.
			self.requestSent = self.SETUP
		
		# Play request
		elif requestCode == self.PLAY and self.state == self.READY:
			# Update RTSP sequence number.

			self.rtspSeq += 1
			print('\nPLAY event\n')
			
			# Write the RTSP request to be sent.
			request = self.__create_request("PLAY")
			
			# Keep track of the sent request.
			self.requestSent = self.PLAY
		
		# Pause request
		elif requestCode == self.PAUSE and self.state == self.PLAYING:
			# Update RTSP sequence number.
			self.rtspSeq += 1
			print('\nPAUSE event\n')
			
			# Write the RTSP request to be sent.
			request = self.__create_request("PAUSE")
			
			# Keep track of the sent request.
			self.requestSent = self.PAUSE
			
		# Teardown request
		elif requestCode == self.TEARDOWN and not self.state == self.INIT:
			# Update RTSP sequence number.
			self.rtspSeq += 1
			print('\nTEARDOWN event\n')
			
			# Write the RTSP request to be sent.
			request = self.__create_request("TEARDOWN")
			
			# Keep track of the sent request.
			self.requestSent = self.TEARDOWN
		else:
			return
		
		# Send the RTSP request using rtspSocket.
		request_bytes = request.encode("utf-8")
		self.rtspSocket.sendall(request_bytes)
		print('\nData sent:\n' + request)
	

	def recvRtspReply(self):
		"""Receive RTSP reply from the server."""
		while True:
			reply = self.rtspSocket.recv(1024)
			
			if reply:
				print("Going to Parse RTSP reply")
				self.parseRtspReply(reply.decode("utf-8"))
			
			# Close the RTSP socket upon requesting Teardown
			if self.requestSent == self.TEARDOWN:
				self.rtspSocket.shutdown(socket.SHUT_RDWR)
				self.rtspSocket.close()
				break
	
	def parseRtspReply(self, data):
		"""Parse the RTSP reply from the server."""
		lines = data.split('\n')
		seqNum = int(lines[1].split(' ')[1])
		
		# Process only if the server reply's sequence number is the same as the request's
		if seqNum == self.rtspSeq:
			session = int(lines[2].split(' ')[1])
			# New RTSP session ID
			if self.sessionId == 0:
				print("New session")
				self.sessionId = session
			
			# Process only if the session ID is the same
			if self.sessionId == session:
				if int(lines[0].split(' ')[1]) == 200: 
					if self.requestSent == self.SETUP:
						#-------------
						# TO COMPLETE
						#-------------
						# Update RTSP state.
						self.state = self.READY
						print("State is ready")
						# Open RTP port.
						self.openRtpPort() 
					elif self.requestSent == self.PLAY:
						self.state = self.PLAYING
						print('\nPLAY sent\n')
					elif self.requestSent == self.PAUSE:
						self.state = self.READY
						
						# The play thread exits. A new thread is created on resume.
						self.playEvent.set()
					elif self.requestSent == self.TEARDOWN:
						self.state = self.TEARDOWN
						
						# Flag the teardownAcked to close the socket.
						self.teardownAcked = 1 
	
	def openRtpPort(self):
		"""Open RTP socket binded to a specified port."""
		#-------------
		# TO COMPLETE
		#-------------
		# Create a new datagram socket to receive RTP packets from the server
		self.rtpSocket = socket.socket(type=socket.SOCK_DGRAM)
		
		# Set the timeout value of the socket to 0.5sec
		self.rtpSocket.settimeout(0.5)
		
		try:
			# Bind the socket to the address using the RTP port given by the client user
			self.rtpSocket.bind((self.serverAddr ,self.rtpPort))
			print('\nBind \n')
		except:
			tkinter.messagebox.showwarning('Unable to Bind', 'Unable to bind PORT=%d' %self.rtpPort)

	def handler(self):
		"""Handler on explicitly closing the GUI window."""
		self.pauseMovie()
		if tkinter.messagebox.askokcancel("Quit?", "Are you sure you want to quit?"):
			self.exitClient()
		else: # When the user presses cancel, resume playing.
			self.playMovie()

