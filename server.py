from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket
import multiprocessing
import urllib2
import json, time
from sets import Set
from pymongo import MongoClient
import dateutil.parser

#leavesURL = 'http://143.107.45.126:30134/collector/resources/164f4961-5e91-4d10-8e70-6e0df691f798/data/last'
#sapFlowURL = 'http://143.107.45.126:30134/collector/resources/d1557e9b-ea3e-45f8-828b-820055230e20/data/last'

leavesURL = 'http://172.17.0.134:8000/collector/resources/164f4961-5e91-4d10-8e70-6e0df691f798/data/last'
sapFlowURL = 'http://172.17.0.134:8000/collector/resources/d1557e9b-ea3e-45f8-828b-820055230e20/data/last'

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

		print url
		print sj
		print '-----------'

		#print sj

		return (sj, j)

p = Pool(2)

def removeOldestEntries(collection):
	#if collection.count() > 1024 * 10:

	if collection.find().count() > 3600 * 24 * 7:
		for record in collection.find().sort([ ("date", 1) ]).limit(1):
			print 'DEL => ', record
			collection.remove({'date': record['date']})

def getProcessedData(idData, data):

	obj = {"resources":
	[
		{
		 "uuid": idData,
		 "data": data
		}
	]
	}

	return json.dumps(obj)

#dbMongo['sapflow'].remove()
#dbMongo['leaves'].remove()
#dbMongo['sapflow'].create_index('date')
#dbMongo['leaves'].create_index('date')

def processDataWorker(lstRef, elapsedTimeAfterHeating):

	import math

	client = MongoClient()
	dbMongo = client['interscity']

	print 'START PROCESSEDDATA', elapsedTimeAfterHeating

	while True:

		lst = []

		i = 0
		lastDate = None
		upperTCList = [ ]
		lowerTCList = [ ]

		lastDay = [ r for r in dbMongo['sapflow'].find().sort([ ("date", -1) ]).limit(12 * 3600) ]

		print 'RUN PROCESSEDDATA', elapsedTimeAfterHeating, 'lastDay =>', len(lastDay)

		heating = 0.
		i = None
		count = False

		#print 'Processing'
		for record in reversed(lastDay):
			#print len(upperTCList)

			if int(record['heating']) == 1 and int(heating) == 0 and not count:
				count = True
				i = dateutil.parser.parse(record['date'])
				upperTCList[:] = []
				lowerTCList[:] = []

			heating = record['heating']

			if count:
				upperTCList.append( record['ads_0_1'] )
				lowerTCList.append( record['ads_2_3'] )

			heating = record['heating']
			d = dateutil.parser.parse(record['date'])

			if i == None:
				i = d

			diff = d - i

			if count and diff.seconds > elapsedTimeAfterHeating:

				count = False

				div = (upperTCList[-1] - upperTCList[0] + 1e-6) / (lowerTCList[-1] - lowerTCList[0]  + 1e-6)

				if div <= 0:
					div = 1.

				lst.append(
					{
					  'x': '%.2d:%.2d' % ((d.hour - 3) % 24, d.minute),
					  'y': '%f' % ( math.log(div) )
					}
				)

				upperTCList = upperTCList[1:]
				lowerTCList = lowerTCList[1:]

		lstRef[:] = lst

		time.sleep(30)

def downloadEverything(lastMessages):

	print 'STARTED'

	client = MongoClient()
	dbMongo = client['interscity']

	while True:

		(sj, objSapFlow) = downloadInParallel(sapFlowURL)
		(sjLeaves, objLeaves) = downloadInParallel(leavesURL)

		dbMongo['sapflow'].insert(objSapFlow['resources'][0]['capabilities']['room_monitoring'][0])
		dbMongo['leaves'].insert(objLeaves['resources'][0]['capabilities']['room_monitoring'][0])

		removeOldestEntries(dbMongo['sapflow'])
		removeOldestEntries(dbMongo['leaves'])

		lastMessages.append(sj)
		lastMessages.append(sjLeaves)

		if len(lastMessages) > 64:
			lastMessages[:] = lastMessages[2:]

		print 'Download'
		print sj, sjLeaves
		print '-------'

		time.sleep(1)

	return

managerMP = multiprocessing.Manager()

listWithDataProcessed = managerMP.list([])
processData = multiprocessing.Process(target=processDataWorker, args=(listWithDataProcessed, 30))
processData.start()

listWithDataProcessed45 = managerMP.list([])
processData45 = multiprocessing.Process(target=processDataWorker, args=(listWithDataProcessed45, 45))
processData45.start()

listWithDataProcessed60 = managerMP.list([])
processData60 = multiprocessing.Process(target=processDataWorker, args=(listWithDataProcessed60, 60))
processData60.start()

lastMessages = managerMP.list([])
processDownload = multiprocessing.Process(target=downloadEverything, args=(lastMessages,))
processDownload.start()

lastTimeProcessedDataWasSent = time.time()
lastTimeProcessRan = time.time()

#client = MongoClient()
#dbMongo = client['interscity']

while True:

	if time.time() - ts > 2:
		ts = time.time()

		#(sj, objSapFlow), (sjLeaves, objLeaves) = p.map(downloadInParallel, [sapFlowURL, leavesURL])

		#dbMongo['sapflow'].insert(objSapFlow['resources'][0]['capabilities']['room_monitoring'][0])
		#dbMongo['leaves'].insert(objLeaves['resources'][0]['capabilities']['room_monitoring'][0])

		#removeOldestEntries(dbMongo['sapflow'])
		#removeOldestEntries(dbMongo['leaves'])

		#print dbMongo['sapflow'].count(), dbMongo['leaves'].count()

		#lastMessages.append(sj)
		#lastMessages.append(sjLeaves)

		#if len(lastMessages) > 64:
		#	lastMessages = lastMessages[2:]

		for c in clients:
			if not c.address in firstMessagesSent:
				for m in lastMessages:
					c.sendMessage(m)

				firstMessagesSent.add(c.address)

				processedData = getProcessedData('processed-data', list(listWithDataProcessed))
				processedData45 = getProcessedData('processed-data-45', list(listWithDataProcessed45))
				processedData60 = getProcessedData('processed-data-60', list(listWithDataProcessed60))
				c.sendMessage(processedData)
				c.sendMessage(processedData45)
				c.sendMessage(processedData60)

			c.sendMessage(lastMessages[-2])
			c.sendMessage(lastMessages[-1])

		if time.time() - lastTimeProcessedDataWasSent > 5:

			for c in clients:
				processedData = getProcessedData('processed-data', list(listWithDataProcessed))
				c.sendMessage(processedData)

			for c in clients:
				processedData = getProcessedData('processed-data-45', list(listWithDataProcessed45))
				c.sendMessage(processedData)

			for c in clients:
				processedData = getProcessedData('processed-data-60', list(listWithDataProcessed60))
				c.sendMessage(processedData)

			lastTimeProcessedDataWasSent = time.time()

		#print sj
		#print sjLeaves
		print '-----'
		print 'LAST'
		print lastMessages[-2]
		print lastMessages[-1]
		print '-----'
		print len( lastMessages ), len(listWithDataProcessed), len(listWithDataProcessed45), len(listWithDataProcessed60)

	server.serveonce()
