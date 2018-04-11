import socket
import queue
import threading

from udsoncan.Request import Request
from udsoncan.Response import Response
from udsoncan import TimeoutException

class SocketConnection(object):
	def __init__(self, sock, bufsize=4095):
		self.rxqueue = queue.Queue()
		self.exit_requested = False
		self.opened = False
		self.rxthread = threading.Thread(target=self.rxthread_task)
		self.sock = sock
		self.sock.settimeout(0.1)	# for recv
		self.bufsize=bufsize


	def open(self):
		self.exit_requested = False
		self.rxthread.start()
		self.opened = True
		return self

	def __enter__(self):
		return self

	def __exit__(self, type, value, traceback):
		self.close()

	def is_open(self):
		return self.opened

	def rxthread_task(self):
		while not self.exit_requested:
			try:
				data = self.sock.recv(self.bufsize)
				if data is not None:
					self.rxqueue.put(data)
			except socket.timeout as e:
				pass
			except Exception as e:
				self.exit_requested = True


	def close(self):
		self.exit_requested = True
		self.opened = False

	def send(self, obj):
		if isinstance(obj, Request) or isinstance(obj, Response):
			payload = obj.get_payload()  
		else :
			payload = obj

		self.sock.send(payload)

	def wait_frame(self, timeout=2, exception=False):
		if not self.opened:
			if exception:
				raise RuntimeError("Connection is not opened")
			else:
				return None

		timedout = False
		frame = None
		try:
			frame = self.rxqueue.get(block=True, timeout=timeout)

		except queue.Empty:
			timedout = True
			
		if exception and timedout:
			raise TimeoutException("Did not received frame in time (timeout=%s sec)" % timeout)

		return frame

	def empty_rxqueue(self):
		while not self.rxqueue.empty():
			self.rxqueue.get()

class IsoTPConnection(object):
	def __init__(self, interface, rxid, txid, tpsock=None):
		import isotp

		self.interface=interface
		self.rxid=rxid
		self.txid=txid
		self.rxqueue = queue.Queue()
		self.exit_requested = False
		self.opened = False

		self.rxthread = threading.Thread(target=self.rxthread_task)
		self.tpsock = isotp.socket(timeout=0.1) if tpsock is None else tpsock


	def open(self):
		self.tpsock.bind(self.interface, rxid=self.rxid, txid=self.txid)
		self.exit_requested = False
		self.rxthread.start()
		self.opened = True
		return self

	def __enter__(self):
		return self

	def __exit__(self, type, value, traceback):
		self.close()

	def is_open(self):
		return self.tpsock.bound

	def rxthread_task(self):
		while not self.exit_requested:
			try:
				data = self.tpsock.recv()
				if data is not None:
					self.rxqueue.put(data)
			except socket.timeout as e:
				pass
			except Exception as e:
				self.exit_requested = True


	def close(self):
		self.exit_requested = True
		self.tpsock.close()
		self.opened = False

	def send(self, obj):
		if isinstance(obj, Request) or isinstance(obj, Response):
			payload = obj.get_payload()  
		else :
			payload = obj

		self.tpsock.send(payload)

	def wait_frame(self, timeout=2, exception=False):
		if not self.opened:
			if exception:
				raise RuntimeError("Connection is not opened")
			else:
				return None

		timedout = False
		frame = None
		try:
			frame = self.rxqueue.get(block=True, timeout=timeout)

		except queue.Empty:
			timedout = True
			
		if exception and timedout:
			raise TimeoutException("Did not received ISOTP frame in time (timeout=%s sec)" % timeout)

		return frame

	def empty_rxqueue(self):
		while not self.rxqueue.empty():
			self.rxqueue.get()