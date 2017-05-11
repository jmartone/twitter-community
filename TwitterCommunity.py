import twitter_functions
import pandas as pd
import numpy as np
import networkx as nx
import joblib
import community
from os import path
from os.path import isfile
from datetime import datetime
from random import shuffle
from bot_or_not import BotOrNot
from itertools import combinations
from itertools import chain
from sklearn.cluster import KMeans
from scipy.linalg import eigvals
from scipy.spatial.distance import pdist
from scipy.spatial.distance import squareform
from collections import defaultdict
from multiprocessing import Pool
from functools import partial
from sys import getsizeof

class TwitterCommunity(object):

	def __init__(self, source = None, filterSpam = True, filterInactive = True,
		filterGenPop = True, userSampleSize = 2000, writeCSVs = True):
		'''Instantiate settings for Twitter Community Analysis'''
		self.source = source
		self.filterSpam = filterSpam
		self.filterInactive = filterInactive
		self.filterGenPop = filterGenPop
		self.userSampleSize = userSampleSize
		self.usersFollowing_set = False
		self.writeCSVs = writeCSVs

	def queryContinue(message, default = True):
		'''Returns True to continue, False to stop'''
		valid = {
			"yes":True,
			"y":True,
			"no":False,
			"n":False
			}
		prompt = " [y/n]: "

		while True:
			sys.stdout.write(text + prompt)
			choice = raw_input().lower()
			toContinue = True
			if default is not None and choice == '':
				toContinue = default
				return toContinue
			elif choice in valid.keys():
				toContinue = valid[choice]
				return toContinue
			else:
				sys.stdout.write("Please respond with 'yes' or 'no' "\
					"(or 'y' or 'n').\n")

	# store large not oft used variables on disk rather than in memory
	@property
	def audience(self):
		'''Loads the audience variable from disk'''
		# usersFollowing is stored on disk to prevent memory overload
		if (isfile("{}_usersFollowing.pkl".format(hash(self)))):
			return(joblib.load("{}_usersFollowing.pkl".format(hash(self))))
		else:
			raise ValueError("The usersFollowing variable has not been set or cannot be found")

	@audience.setter
	def audience(self, value):
		'''Saves the audience variable to disk'''
		if (type(value) != list):
			raise ValueError("Audience must be a list")
		else:
			joblib.dump(value, "{}_usersFollowing.pkl".format(hash(self)))

	@property
	def audience_labeled(self):
		'''Loads the audience_labeled variable from disk'''
		# usersFollowing is stored on disk to prevent memory overload
		if (isfile("{}_audience_labeled.pkl".format(hash(self)))):
			return(joblib.load("{}_audience_labeled.pkl".format(hash(self))))
		else:
			raise ValueError("The audience_labeled variable has not been set or cannot be found")

	@audience_labeled.setter
	def audience_labeled(self, value):
		'''Saves the audience_labeled variable to disk'''
		joblib.dump(value, "{}_audience_labeled.pkl".format(hash(self)))

	@property
	def audience_follows(self):
		'''Loads the audience_labeled variable from disk'''
		# usersFollowing is stored on disk to prevent memory overload
		if (isfile("{}_audience_follows.pkl".format(hash(self)))):
			return(joblib.load("{}_audience_follows.pkl".format(hash(self))))
		else:
			raise ValueError("The audience_follows variable has not been set or cannot be found")

	@audience_follows.setter
	def audience_follows(self, value):
		'''Saves the audience_labeled variable to disk'''
		joblib.dump(value, "{}_audience_follows.pkl".format(hash(self)))

	def _collectFollowers(self, user, count = float('inf')):
		'''Collect the given user's followers'''
		followers = twitter_functions.getFollowers(user)
		if (followers) and (self.writeCSVs): pd.Series(followers).to_csv("all_{}_followers.csv".format(user), index = False)
		return(followers)

	def getAudienceFromFollowers(self, source = None, followersToSample = float('inf'), skipOnError = True):
		'''Public function to collect followers from either a list or a single handle'''

		if (source is not None):
			self.source = source
		followers = []

		# if input is only one user convert to list
		if (type(self) != list):
			source = [source]

		# cycle through each user and append their followers to the followers list
		for user in source:
			workingFollowers = self._collectFollowers(user, count = followersToSample)
			if (workingFollowers):
				followers.extend(workingFollowers)
			# optional error handling
			elif (skipOnError):
				if (not self.queryContinue("Could not collect {}'s followers, continue?".format(user))):
					raise ValueError("Could not collect {}'s followers, continue?".format(user))
			else:
				raise ValueError("Could not collect {}'s followers, continue?".format(user))

		if (self.writeCSVs): pd.Series(followers).to_csv("all_{}_followers.csv".format(hash(self)), index = False)

		self.audience = followers
		return(followers)

	def assessUsers(self, users = None, returnId = True, goal = float('inf'),
			setSize = 100, followingMin = 2, followingMax = 5000, daysInactive = 365,
			minTweets = 4, filterSpam = True, spamScore = 0.5, trim = True):
		'''Analyzes a given list of users and returns a list of tuples in the format (user, label)'''

		if (users == None):
			users = self.audience
		else:
			self.audience = users

		bot_checker = BotOrNot() if filterSpam else None
		today = datetime.now()
		analyzedUsers = []
		userLabels = []
		goalCount = float('inf')
		# if goal is a decimal, interpret it as a percentage
		if (goal < 1) and (goal > 0):
			goalCount = ceil(len(users)*goal)
		elif (goal < float('inf')):
			goalCount = goal

		# if looking for a sample of valid users, shuffle the list
		if (goalCount < float('inf')):
			shuffle(users)

		while(userLabels.count('valid') < goalCount) and (len(users) > 0):
			workingActiveUsers = []
			# splice out the working user list
			workingUsers = users[:setSize]
			users = users[setSize:]
			hydratedUsers = twitter_functions.hydrateUsers(workingUsers)

			# analyze basic user metrics
			for user in hydratedUsers:
				if (returnId):
					print("Checking {}".format(user['id']))
				else:
					print("Checking {}".format(user['screen_name']))
				userLabel = "valid"
				if (user['protected']):
					print("User is private, dropping")
					userLabel = "private"
				elif (user['friends_count'] > followingMax):
					print("User is following over {} users, dropping".format(followingMax))
					userLabel = "over_following"
				elif (user['friends_count'] < followingMin):
					print("User is following less than {} users, dropping".format(followingMin))
					userLabel = "under_following"
				elif(user['statuses_count'] < minTweets) or (not user.get('status', False)):
					print("User has tweeted fewer than {} times".format(minTweets))
					userLabel = "too_few_tweets"
				elif ((today-datetime.strptime(user['status']['created_at'], '%a %b %d %H:%M:%S +0000 %Y')).days + 1 > daysInactive): #tweeted too long ago therefore inactive
					print("User has not tweeted in more than {} days".format(daysInactive))
					userLabel = "inactive"
				elif (filterSpam):
					result = bot_checker.check_account(user['id'])
					if (result['score'] >= spamScore):
						print("User received a spam score greater than or equal to {}".format(spamScore))
						userLabel = "spam"

				analyzedUsers.append(user['id'] if returnId else user['screen_name'])
				userLabels.append(userLabel)
				self.audience_labeled = zip(analyzedUsers, userLabels)

		if (trim):
			validUsers = []
			for user, label in zip(analyzedUsers, userLabels):
				if (label == 'valid'):
					validUsers.append(user)
			return(validUsers)
		else:
			return zip(analyzedUsers, userLabels)

	def getFollowLists(self, users = None):
		'''Get a list of what accounts each user follows and reutrn a list of tuples of (user, usersFollowed)'''
		if (users == None):
			users = self.audience
		else:
			self.audience = users

		followedUsers = []
		for user in users:
			print("Collecting the users followed by {}".format(user))
			workingFollowedUsers = twitter_functions.getUsersFollowed(user)
			if (workingFollowedUsers):
				print("Collected {} followed users".format(len(workingFollowedUsers)))
				followedUsers.append(workingFollowedUsers)
			else:
				print("Could not collect user's followers.")
				# append an empty list so that the zip doesn't break
				followedUsers.append([])

		self.audience_follows = zip(users, followedUsers)
		return(zip(users, followedUsers))

	def followerOverlap(self, audience_follows = None, trimFrequencyOutliers = True,
		minFollowers = 0, maxFollowers = float('inf'), dropOnes = True,
		dropUbiquitous = True, returnList = True, trimGenPop = True):
		'''Finds the frequency of each account in the followLists, automatically removing accounts followed by 1'''
		if (audience_follows == None):
			audience_follows = self.audience_follows
		else:
			self.audience_follows = audience_follows
			self.audience = zip(*audience_follows)[0]

		audience, followLists = zip(*audience_follows)[0]
		followed = pd.Series(list(chain.from_iterable(followLists))).value_counts()

		# drop accounts only followed by one person in the sample -- these will not contribute edges to the network and are USELESS
		if (dropOnes):
			followed = followed[followed > 1]

		# drop accounts followed by everyone in the sample
		if (dropUbiquitous):
			followed = followed[followed < len(audience)]

		# use interquartile range to identify outliers by the frequency of their follower count
		if (trimFrequencyOutliers):
			followed = self._trimFrequencyOutliers(followed)

		followed = followed.reset_index()
		followed.columns = ['user', 'weight']
		followed.loc[:, 'p'] = followed.loc[:, 'weight']/float(len(audience))

		followed = self._compareToGenPop(followed, len(audience), trim = trimGenPop)

		# add handles and follower counts to each user in the list
		followed.loc[:, ['handle', 'followers']] = ['N/A', 'N/A']
		for user in twitter_functions.hydrateUsers(followed['user'].tolist()):
		    followed.loc[followed['user'] == str(user['id']), ['handle', 'followers']] = [user['screen_name'], user['followers_count']]

		# trim accounts to those within the follower range
		if (minFollowers > 0) or (maxFollowers < float('inf')):
			followed = followed.loc[followed['followers'] >= minFollowers, :]
			followed = followed.loc[followed['followers'] <= maxFollowers, :]

		self.followed = followed
		if (returnList):
			return(followed['user'].tolist())
		else:
			return(followed)

	def _trimFrequencyOutliers(self, followed):
		'''use interquartile range to identify outliers by the frequency of their follower count'''
		# count the frequency of each number of followers
		frequencies = followed.value_counts()
		# calculate interquartile range for occurences of a follower count
		quartile = int(round(len(countOfFollowings)/4.0))
		# counts are in descending order so Q1 - Q3
		iqr = countOfFollowings.iloc[quartile] - countOfFollowings.iloc[quartile*3]
		# cut off Q1 + 1.5IQR
		outlierCutoff = int(round(countOfFollowings[quartile] + 1.5 * iqr))
		minNumFollowers = frequencies.loc[frequencies < outlierCutoff].index.sort_values(ascending = True)[0]
		print("Removing users followed by fewer than {} users from the sample".format(minNumFollowers))
		followed = followed.loc[followed >= minNumFollowers]
		print("Shortened to {} followed users".format(len(followed)))
		return(followed)

	def _compareToGenPop(self, followed, sampleSize, confidence = 0.99, tails = 2, trim = True):
		critical = 0
		if (tails == 2):
			if (confidence == 0.99):
				critical = 2.58
			elif (confidence == 0.95):
				critical = 1.96
		elif (tails == 1):
			if (confidence == 0.99):
				critical = 2.33
			elif (confidence == 0.95):
				critical = 1.645
			if (confidence == -0.99):
				critical = -2.33
			elif (confidence == -0.95):
				critical = -1.645

		size_genPop = 2000.
		sampleSize = float(sampleSize)

		# load general population follower overlap
		genPop = pd.read_csv('US_genpop_relevent_2000_followings.csv', header = None)
		genPop.columns = ['user', 'weight_genPop']
		genPop.loc[:, 'user'] = genPop.loc[:, 'user'].astype('string')
		genPop.loc[:, 'p_genPop'] = genPop.loc[:, 'weight_genPop'] / size_genPop

		# merge along users present in both lists
		compare = genPop.merge(followed, how = 'inner', on = 'user')

		# calculate the z-score for the sample v. genPop
		# z-score formula
		# (p_toCompare - p_genPop) / sqrt(p_hat*(1-p_hat)*(1/size_genPop + 1/sampleSize))
		p_hat = (compare['weight_genPop'] + compare['weight']) / (size_genPop+sampleSize)
		compare['z_score'] = (compare['p'] - compare['p_genPop'])/np.sqrt(p_hat*(1-p_hat) * (1/size_genPop + 1/sampleSize))

		# create an index comparing the proportion of users from the sample v. the propotion in the general population
		compare['indexed'] = (compare['p']/compare['p_genPop'])*100
		compare['indexed'] = compare['indexed'].round()

		# find usersFollowed present in the sample, but absent from the general population to append to the compared list
		extra = followed.loc[np.logical_not(followed['user'].isin(compare['user']))]
		toAdd = pd.DataFrame({
			'user': extra['user'],
			'weight': extra['weight'],
			'z_score': [float('inf') for _ in range(len(extra))],
			'indexed': [float('inf') for _ in range(len(extra))],
			'p':extra['p']
			})
		compare = compare.append(toAdd)

		# trim to users that are statistically significant
		if (trim):
			print("Removing users followed likely due to chance")
			if (tails > 1):
				compare = compare[compare['z_score'].abs() > critical]
			elif (critical < 0):
				compare = compare[compare['z_score'] < critical]
			elif (critical > 0):
				compare = compare[compare['z_score'] > critical]
			print("Shortened to {} users".format(len(compare)))