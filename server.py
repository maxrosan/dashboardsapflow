from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket
from multiprocessing
import urllib2
import json, time
from sets import Set
from pymongo import MongoClient

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

		return (sj, j)

client = MongoClient()
dbMongo = client['interscity']

p = Pool(2)

def removeOldestEntries(collection):
	#if collection.count() > 1024 * 10:
	if collection.find().count() > 3600 * 24 * 7:
		for record in collection.find().sort([ ("date", 1) ]).limit(1):
			print 'DEL => ', record
			collection.remove({'date': record['date']})

def getProcessedData():

	obj = {"resources":
	[
		{
		 "uuid":"processed-data",
		 "data": [ 0 ] * 3600 * 24
		}
	]
	}

	return json.dumps(obj)

#dbMongo['sapflow'].remove()
#dbMongo['leaves'].remove()
dbMongo['sapflow'].create_index('date')
dbMongo['leaves'].create_index('date')

while True:

	if time.time() - ts > 1:
		ts = time.time()

		(sj, objSapFlow), (sjLeaves, objLeaves) = p.map(downloadInParallel, [sapFlowURL, leavesURL])

		dbMongo['sapflow'].insert(objSapFlow['resources'][0]['capabilities']['room_monitoring'][0])
		dbMongo['leaves'].insert(objLeaves['resources'][0]['capabilities']['room_monitoring'][0])

		removeOldestEntries(dbMongo['sapflow'])
		removeOldestEntries(dbMongo['leaves'])

		print dbMongo['sapflow'].count(), dbMongo['leaves'].count()

		lastMessages.append(sj)
		lastMessages.append(sjLeaves)

		if len(lastMessages) > 64:
			lastMessages = lastMessages[2:]


		for c in clients:
			if not c.address in firstMessagesSent:
				for m in lastMessages:
					c.sendMessage(m)
				processedData = getProcessedData()
				c.sendMessage(processedData)
				firstMessagesSent.add(c.address)
			c.sendMessage(sj)
			c.sendMessage(sjLeaves)

		print sj
		print sjLeaves

	server.serveonce()
