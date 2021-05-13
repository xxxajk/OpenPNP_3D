#!/usr/bin/env python3
import sys
import traceback

try:
	import logging
	import picamera
	from picamera.array import PiRGBArray
	import io
	import time
	import smbus
	import socket
	import select
	import threading
	from threading import Condition
	import gc
	import struct
	import math
	import copy
	import os
except:
	traceback.print_exc()
	sys.exit(1)

class ReadWriteLock:
	def __init__(self):
		self._read_ready = threading.Condition(threading.Lock())
		self._readers = 0

	def acquire_read(self):
		self._read_ready.acquire()
		try:
			self._readers += 1
		finally:
			self._read_ready.release()

	def release_read(self):
		self._read_ready.acquire()
		try:
			self._readers -= 1
			if not self._readers:
				self._read_ready.notifyAll()
		finally:
			self._read_ready.release()

	def acquire_write(self):
		self._read_ready.acquire()
		while self._readers > 0:
			self._read_ready.wait()

	def release_write(self):
		self._read_ready.release()

class StreamingOutput(object):
	def __init__(self):
		self.frame = None
		self.buffer = io.BytesIO()
		self.condition = Condition()

	def write(self, buf):
		if buf.startswith(b'\xff\xd8'):
			# New frame, copy the existing buffer's content and notify all
			# clients it's available
			self.buffer.truncate()
			with self.condition:
				datalock.acquire_write()
				self.frame = self.buffer.getvalue()
				datalock.release_write()
				self.condition.notify_all()
		self.buffer.seek(0)
		return self.buffer.write(buf)

class FrameSegment(object):
	""" 
	Object to break down image frame segment
	if the size of image exceed maximum datagram size 
	"""
	def __init__(self, sock):
		self.s = sock
		self.pp = 0

	def udp_frame(self, data, addr, port):
		""" 
		Break down frame into data segments 
		"""
		size = len(data)
		count = math.ceil(size/(32765))
		packets = count
		array_pos_start = 0
		while count:
			array_pos_end = min(size, array_pos_start + 32765)
			try:
				select.select([], [self.s], [], (30/1000))
				self.s.sendto(struct.pack("BBB", count, packets, self.pp) + data[array_pos_start:array_pos_end], (addr, port))
			except Exception as e:
				break
			array_pos_start = array_pos_end
			count -= 1
		self.pp += 1
		if self.pp > 255:
			self.pp = 0
			

class UDPthread (threading.Thread):
	def __init__(self, sock):
		threading.Thread.__init__(self)
		self.going = False
		self.s = sock
		self.fs = FrameSegment(self.s)
		self.port = 0
		self.addr = ''
		self.addrlock = ReadWriteLock()
	
	def run(self):
		self.going = True
		try:
			with output.condition:
				output.condition.wait(1)
		except:
			self.going = False
		while self.going:
			if self.port > 0:
				with output.condition:
					try:
						output.condition.wait(1)
						datalock.acquire_read()
						frame = copy.copy(output.frame)
						datalock.release_read()
						self.fs.udp_frame(frame, self.addr, self.port)
					except:
						traceback.print_exc()
						self.going = False
			else:
				time.sleep(0.001)

	def death(self):
		self.going = False
	
	def newport(self, address, port):
		self.addrlock.acquire_write()
		self.addr = address
		self.port = port
		self.addrlock.release_write()

datalock=ReadWriteLock()
 
#def main():
#	global datalock
	# no need to modify these placeholders
#	global camwid
#	global camhig
#	global fps
#	global rotation

n = os.fork()
if n > 0:
	pass
else:
	with picamera.PiCamera() as camera:
		# no need to modify these placeholders
		camwid = 640
		camhig = 480
		fps = 30
		rotation = 0
		dietime=-1
		last_por=0
		last_add=''
		camera.framerate=fps
		camera.resolution = (camwid, camhig)
		camera.rotation = rotation
		# 'off' 'auto' 'sunlight' 'cloudy' 'shade' 'tungsten'
		# 'fluorescent' 'incandescent' 'flash' 'horizon'
		camera.awb_mode = 'shade'
		camera.exposure_mode = 'off'
		#camera.exposure_mode = 'fixedfps'
		#camera.shutter_speed = 33
		s = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
		s.setblocking(0)
		s.bind(('::', 12345))
		output = StreamingOutput()
		udpstream = UDPthread(s)
		try:
			udpstream.start()
			camera.start_recording(output, format='mjpeg')
			while 1:
				try:
					select.select([s],[],[],0.01)
					key, addrport=s.recvfrom(32768)
					cmd, arg = struct.unpack("<cL", key)
					add, por, a, b=addrport
					if add != last_add and por != last_por:
						last_add = add
						last_por = por
					elif cmd == b'x': # set video width
						if camera.recording:
							camera.stop_recording()
						camwid = arg
						camera.resolution = (camwid, camhig)
						camera.start_recording(output, format='mjpeg')
					elif cmd == b'y': # set video height
						if camera.recording:
							camera.stop_recording()
						camhig = arg
						camera.resolution = (camwid, camhig)
						camera.start_recording(output, format='mjpeg')
					elif cmd == b'r': # set video frame rate
						if camera.recording:
							camera.stop_recording()
						camera.framerate=arg
						camera.start_recording(output, format='mjpeg')
					elif cmd == b'a': # set camera rotation
						if camera.recording:
							camera.stop_recording()
						camera.rotation=arg						
						camera.start_recording(output, format='mjpeg')
					elif cmd == b'q': # quit UDP stream
						if camera.recording:
							camera.stop_recording()
						udpstream.newport(add, 0)
					elif cmd == b's': # start UDP stream
						udpstream.newport(add, por)
					elif cmd == b'p': # ping
						dietime = 200
				except BlockingIOError:
					if dietime > 0:
						dietime -= 1
					elif dietime == 0: # didn't see a ping in time, stop streaming
						dietime = -1
						udpstream.newport(add, 0)
				except Exception as e:
					print(e)
					traceback.print_exc()
		finally:
			udpstream.death()
			udpstream.join()
			s.close()
			if camera.recording:
				camera.stop_recording()
			camera.close()

