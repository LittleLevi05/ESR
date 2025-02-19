from random import randint
import sys
import traceback
import threading
import socket
import pickle


# append the path of the
# parent directory
from RtpPacket import RtpPacket
from VideoStream import VideoStream
sys.path.append("..")

from topology.ProtocolPacket import ProtocolPacket

class ServerWorker:
    SETUP = 'SETUP'
    PLAY = 'PLAY'
    PAUSE = 'PAUSE'
    TEARDOWN = 'TEARDOWN'

    INIT = 0
    READY = 1
    PLAYING = 2
    state = INIT

    OK_200 = 0
    FILE_NOT_FOUND_404 = 1
    CON_ERR_500 = 2

    clientInfo = {}

    media_prefix = "media/"

    def __init__(self, clientInfo, filename):
        self.clientInfo = clientInfo
        self.filename = self.__add_prefix(filename)

        self.clientInfo['videoStream'] = VideoStream(self.filename)
        self.state = self.READY

    def __add_prefix(self, filename):
        return self.media_prefix + filename

    def run(self):
        threading.Thread(target=self.recvRtspRequest).start()

    def recvRtspRequest(self):
        """Receive RTSP request from the client."""
        try:
            server_socket = socket.socket()
            server_socket.bind(("0.0.0.0", 20004))
            server_socket.listen(2)
            while True:
                conn, address = server_socket.accept()
                self.demultiplexer(conn, address)
        finally:
            server_socket.close()

    def demultiplexer(self, conn, address):
        try:
            data = conn.recv(256)
            packet = pickle.loads(data)

            #print("RECEBI MENSAGEM")
            if packet.opcode == '1':
                print("Recebi opcode1 para começar Stream")
                # received a request to start the stream
                if self.state == self.READY:
                    self.clientInfo["rtpSocket"] = socket.socket(
                        socket.AF_INET, socket.SOCK_DGRAM)
                    self.state = self.PLAYING
                    self.clientInfo['event'] = threading.Event()
                    self.clientInfo['worker'] = threading.Thread(
                        target=self.sendRtp)
                    self.clientInfo['worker'].start()
            elif packet.opcode == '2':
                # received a request to stop the stream
                if self.state == self.PLAYING:
                    self.state = self.READY
                    self.clientInfo['event'].set()
        finally:
            conn.close()

# def processRtspRequest(self, data):
#		"""Process RTSP request sent from the client."""
# # Get the request type
#		request = data.split('\n')
#		line1 = request[0].split(' ')
#		requestType = line1[0]
#
# # Get the media file name
#		filename = line1[1]
#		filename = self.__add_prefix(filename)
#
# # Get the RTSP sequence number
#		seq = request[1].split(' ')
#
# # Process SETUP request
# if requestType == self.SETUP:
# if self.state == self.INIT:
# # Update state
#				print("processing SETUP\n")
#
# try:
#					self.clientInfo['videoStream'] = VideoStream(filename)
#					self.state = self.READY
# except IOError:
#					self.replyRtsp(self.FILE_NOT_FOUND_404, seq[1])
#
# # Generate a randomized RTSP session ID
#				self.clientInfo['session'] = randint(100000, 999999)
#
# # Send RTSP reply
#				self.replyRtsp(self.OK_200, seq[1])
#
#
# # Process PLAY request
# elif requestType == self.PLAY:
# if self.state == self.READY:
#				print("processing PLAY\n")
#				self.state = self.PLAYING
#
# # Create a new socket for RTP/UDP
#				self.clientInfo["rtpSocket"] = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#
#				self.replyRtsp(self.OK_200, seq[1])
#
# # Create a new thread and start sending RTP packets
#				self.clientInfo['event'] = threading.Event()
#				self.clientInfo['worker']= threading.Thread(target=self.sendRtp)
# self.clientInfo['worker'].start()
#
# # Process PAUSE request
# elif requestType == self.PAUSE:
# if self.state == self.PLAYING:
#				print("processing PAUSE\n")
#				self.state = self.READY
#
# self.clientInfo['event'].set()
#
#				self.replyRtsp(self.OK_200, seq[1])
#
# # Process TEARDOWN request
# elif requestType == self.TEARDOWN:
#			print("processing TEARDOWN\n")
#
# self.clientInfo['event'].set()
#
#
#			self.replyRtsp(self.OK_200, seq[1])
#
# # Close the RTP socket
# self.clientInfo['rtpSocket'].close()

    def sendRtp(self):
        """Send RTP packets over UDP."""
        
        print("A enviar pacotes da stream para o root node ", self.clientInfo['address'], " para porta: ", self.clientInfo['rtpPort'])
        while True:
            #print("A enviar pacotes da stream para o root node ", self.clientInfo['address'], " para porta: ", self.clientInfo['rtpPort'])
            self.clientInfo['event'].wait(0.05)

            # Stop sending if request is PAUSE or TEARDOWN
            if self.clientInfo['event'].isSet():
                print("Vou parar")
                break

            data = self.clientInfo['videoStream'].nextFrame()
            #O filme chegou ao fim
            if data == None:
                self.clientInfo['videoStream'] = VideoStream(self.filename)
                data = self.clientInfo['videoStream'].nextFrame()

            group = str(self.clientInfo['group'])
            packet = ProtocolPacket(group, data)
            data = pickle.dumps(packet)
            if data:
                frameNumber = self.clientInfo['videoStream'].frameNbr()
                try:
                    # print("A enviar pacotes da stream para o root node ", address)
                    address = self.clientInfo['address']
                    port = int(self.clientInfo['rtpPort'])
                    self.clientInfo['rtpSocket'].sendto(
                        self.makeRtp(data, frameNumber), (address, port))
                except:
                    print("Connection Error")
                    # print('-'*60)
                    # traceback.print_exc(file=sys.stdout)
                    # print('-'*60)

    def makeRtp(self, payload, frameNbr):
        """RTP-packetize the video data."""
        version = 2
        padding = 0
        extension = 0
        cc = 0
        marker = 0
        pt = 26  # MJPEG type
        seqnum = frameNbr
        # group
        ssrc = 0

        rtpPacket = RtpPacket()

        rtpPacket.encode(version, padding, extension, cc,
                         seqnum, marker, pt, ssrc, payload)

        return rtpPacket.getPacket()

    def replyRtsp(self, code, seq):
        """Send RTSP reply to the client."""
        if code == self.OK_200:
            print("200 OK REPLYING RTSP")
            reply = 'RTSP/1.0 200 OK\nCSeq: ' + seq + \
                '\nSession: ' + str(self.clientInfo['session'])
            connSocket = self.clientInfo['rtspSocket'][0]
            connSocket.send(reply.encode())

        # Error messages
        elif code == self.FILE_NOT_FOUND_404:
            print("404 NOT FOUND")
        elif code == self.CON_ERR_500:
            print("500 CONNECTION ERROR")
