from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket
from multiprocessing import Process, Queue
from multiprocessing import Process, Value, Array
import urllib2
import json, time
from sets import Set

leavesURL = 'http://143.107.45.126:30134/collector/resources/164f4961-5e91-4d10-8e70-6e0df691f798/data/last'
sapFlowURL = 'http://143.107.45.126:30134/collector/resources/d1557e9b-ea3e-45f8-828b-820055230e20/data/last'

def downloadJson(url):
	request = urllib2.Request(url)
	#request = urllib2.Request('https://dweet.io/get/latest/dweet/for/room118b')
	request.get_method = lambda: 'POST'
	#request.get_method = lambda: 'GET'
	response = urllib2.urlopen(request)
	jsonFile = json.load(response)
	return jsonFile

clients = []
lastMessages = []
firstMessagesSent = Set([])

class SimpleChat(WebSocket):

	def handleConnected(self):
		print(self.address, 'connected')
		#for client in clients:
		#	client.sendMessage(self.address[0] + u' - connected')
		clients.append(self)

	def handleClose(self):
		clients.remove(self)
		print(self.address, 'closed')
		firstMessagesSent.remove(self.address)
		#for client in clients:
		#	client.sendMessage(self.address[0] + u' - disconnected')

server = SimpleWebSocketServer('', 8000, SimpleChat)

ts = time.time()

from multiprocessing import Pool

def downloadInParallel(url):
		j = downloadJson(url)
		sj = json.dumps(j)
		return sj

p = Pool(2)

while True:

	if time.time() - ts > 1:
		ts = time.time()

		sj, sjLeaves = p.map(downloadInParallel, [sapFlowURL, leavesURL])

		lastMessages.append(sj)
		lastMessages.append(sjLeaves)

		if len(lastMessages) > 64:
			lastMessages = lastMessages[2:]


		for c in clients:
			if not c.address in firstMessagesSent:
				for m in lastMessages:
					c.sendMessage(m)
				firstMessagesSent.add(c.address)
			c.sendMessage(sj)
			c.sendMessage(sjLeaves)

		print sj
		print sjLeaves

	server.serveonce()
