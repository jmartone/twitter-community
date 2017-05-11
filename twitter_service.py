import tweepy
import time
import threading
import json

def threaded(fn):
    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=fn, args=args, kwargs=kwargs)
        thread.setDaemon(True)
        thread.start()
        return thread
    return wrapper

class TwitterService:

	limited = [False for _ in CREDS]
	available = threading.Event()

	@threaded
	def cycleLimit(self, limitedCycle, available):
		time.sleep(60*15+1)
		self.limited[limitedCycle] = False
		available.set()

	def printCycleStatus(self):
		print("{} cycle(s) remaining".format(self.limited.count(False)))

	def getAPI(self):
		return self.twitterAPI

	def updateConnection(self):
		self.twitterAuth = tweepy.OAuthHandler(self.CREDS[self.cycle]['CONSUMER_KEY'], self.CREDS[self.cycle]['CONSUMER_SECRET'])
		self.twitterAuth.set_access_token(self.CREDS[self.cycle]['ACCESS_TOKEN'], self.CREDS[self.cycle]['ACCESS_TOKEN_SECRET'])
		self.twitterAPI = tweepy.API(self.twitterAuth, parser=tweepy.parsers.JSONParser())
		if (self.verbose):
			print("Accessing the api as {}".format(self.CREDS[self.cycle]['NAME']))

	def hitLimit(self):
		if (self.verbose):
			print("Attempting to cycle authentication")
		self.limited[self.cycle] = True
		self.cycleLimit(self.cycle, self.available)
		if any(not limit for limit in self.limited):
			self.cycleAuth()
		else:
			print("Waiting for an authentication to open")
			self.available.clear()
			while not self.available.wait(1):
				pass
			self.cycleAuth()

	def cycleAuth(self):
		for c, limit in enumerate(self.limited):
			if (not limit):
				self.cycle = c
				break

		self.updateConnection()
		if (self.verbose):
			print("Authentication cycled")
			self.printCycleStatus()

	def __init__(self, credsFile, verbose = False):
		if (verbose):
			print("Establishing connection")
		with open(credsFile, 'r') as creds:
			self.CREDS = json.loads(creds.read())
		self.verbose = verbose
		self.cycle = 0
		self.updateConnection()