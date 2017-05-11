from twitter_service import TwitterService
from tweepy import TweepError
import re

def getUsersFollowed(user, service = TwitterService('twitterCreds.json', verbose = True)):
	usersFollowed = []
	nextPage = -1
	while True:
		try:
			workingUsersFollowed = None
			cursors = None
			response, cursors = service.getAPI().friends_ids(user, cursor = nextPage, stringify_ids = True)

			workingUsersFollowed = response['ids']
			# nextPage = response['next_cursor']
			nextPage = cursors[1]

			usersFollowed.extend(workingUsersFollowed)

			if (nextPage <= 0):
				break
		except TweepError as e:
			if (type(e.message[0]) == dict) and ('code' in e.message[0]):
				# Sorry, that page does not exist
				if (e.message[0]['code'] == 34):
					print('User not found, cannot collect users followed')
					return False
				# Rate limit exceeded
				elif (e.message[0]['code'] == 88):
					print('Followed rate limit hit')
					service.hitLimit()
			# User is private
			elif (str(e).lower().find('not authorized') >= 0):
				print('User is private, cannot collect followers')
				return False
			# User is not found
			elif (str(e).lower().find('does not exist') >= 0):
				print('User does not exist')
				return False
			# other generic error
			else:
				print('Error, trying again')
	return usersFollowed

def getFollowers(user, count = float('inf'), service = TwitterService('twitterCreds.json', verbose = True)):
	followers = []
	nextPage = -1
	while True:
		try:
			workingFollowers = None
			cursors = None
			response, cursors = service.getAPI().followers_ids(user, cursor = nextPage, stringify_ids = True)
			workingFollowers = response['ids']
			nextPage = cursors[1]

			# if collecting a certain number of followers, check if the returned list needs to be spliced
			if (count < float('inf')):
				if (count < len(workingFollowers)):
					workingFollowers = workingFollowers[:count]
				elif ((count - len(followers)) > len(workingFollowers)):
					workingFollowers = workingFollowers[:(count - len(followers))]

			# append the new followers to the list
			followers.extend(workingFollowers)

			# end if the count of followers is reached OR there are no more pages
			if (len(followers) >= count) or (nextPage <= 0):
				break
		except TweepError as e:
			if (type(e.message[0]) == dict) and ('code' in e.message[0]):
				# Sorry, that page does not exist
				if (e.message[0]['code'] == 34):
					print('User not found, cannot collect followers')
					return False
				# Rate limit exceeded
				elif (e.message[0]['code'] == 88):
					print('Followers rate limit hit')
					service.hitLimit()
			# User is private
			elif (str(e).lower().find('not authorized') >= 0):
				print('User is private, cannot collect followers')
				return False
			# User is not found
			elif (str(e).lower().find('does not exist') >= 0):
				print('User does not exist')
				return False
			# other generic error
			else:
				print('Error, trying again')
	return followers

def getTimeline(user, count = 200, service = TwitterService('twitterCreds.json', verbose = True), extended = True):
	timeline = []
	page = 1
	while (len(timeline) < count):
		try:
			workingTimeline = None
			if (extended == True):
				workingTimeline = service.getAPI().user_timeline(user, count = 200, page = page, tweet_mode = 'extended')
			else:
				workingTimeline = service.getAPI().user_timeline(user, count = 200, page = page)
			page += 1

			if (workingTimeline):
				timeline.extend(workingTimeline)
				if (len(timeline) > count):
					timeline = timeline[:count]
			else:
				break

		except TweepError as e:
			if (type(e.message[0]) == dict) and ('code' in e.message[0]):
				# Sorry, that page does not exist
				if (e.message[0]['code'] == 34):
					print('User not found, cannot collect followers')
					return False
				# Rate limit exceeded
				elif (e.message[0]['code'] == 88):
					print('Timeline rate limit hit')
					service.hitLimit()
			# User is private
			elif (str(e).lower().find('not authorized') >= 0):
				print('User is private, cannot collect followers')
				return False
			# User is not found
			elif (str(e).lower().find('does not exist') >= 0):
				print('User does not exist')
				return False
			# other generic error
			else:
				print('Error, trying again')

	return timeline

def hydrateUsers(users, setSize = 100, asId = None, service = TwitterService('twitterCreds.json', verbose = True)):
	hydratedUsers = []

	# allows the user to force screen_names if all of the given users' handles happen to be purely numeric...somehow
	if (asId == None):
		# if any of the users contain anything other than numbers treat the list as screen_names
		asId = True
		for user in users:
			if re.search(r'[^0-9]', str(user)):
				asId = False
				break

	#hydrate users with the API setSize at a time
	while (len(users) > 0):
		# splice out a subset of setSize users to hydrate from the users list
		workingUsers = users[:setSize]
		users = users[setSize:]

		while (True):
			try:
				workingHydratedUsers = None
				if (asId):
					workingHydratedUsers = service.getAPI().lookup_users(user_ids = workingUsers, include_entities = True)
				else:
					workingHydratedUsers = service.getAPI().lookup_users(screen_names = workingUsers, include_entities = True)
				hydratedUsers.extend(workingHydratedUsers)
				break
			except TweepError as e:
				if (type(e.message[0]) == dict) and ('code' in e.message[0]):
					# None of the users were found
					if (e.message[0]['code'] == 17):
						print("None of the users in the subset were found")
						break
					# Rate limit exceeded
					elif (e.message[0]['code'] == 88):
						print('Hydration rate limit hit')
						service.hitLimit()
				# other generic error
				else:
					print('Error, trying again')

	return hydratedUsers

def getSearchResults(q, service = TwitterService('twitterCreds.json', verbose = True)):
    results = []
    page = 1
    while True:
        try:
            workingResults = service.getAPI().search(q = q, count = 100)
            if (workingResults['statuses']):
                results.extend(workingResults['statuses'])
                break
            else:
                break

        except TweepError as e:
            if (type(e.message[0]) == dict) and ('code' in e.message[0]):
                # Rate limit exceeded
                if (e.message[0]['code'] == 88):
                    print('Search rate limit hit')
                    service.hitLimit()
            # other generic error
            else:
                print('Error, trying again')

    return results