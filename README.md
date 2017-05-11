# twitter-community

A tool for analyzing communities on twitter based on a list of users or a handle's followers.

Requires authentication information in one JSON file `twitter_creds.json` with the following format:

	[
		{
			"CONSUMER_KEY": "[CONSUMER_KEY]",
			"CONSUMER_SECRET": "[CONSUMER_SECRET]",
			"ACCESS_TOKEN": "[ACCESS_TOKEN]",
			"ACCESS_TOKEN_SECRET": "[ACCESS_TOKEN_SECRET]"
		}
	]

__Dependencies__
* [Tweepy](https://github.com/tweepy/tweepy) (_NOTE:_ wrapped in twitter_service.py to handle errors)
* [Pandas](https://github.com/pandas-dev/pandas)
* [Scikit-learn](https://github.com/scikit-learn/scikit-learn)
* [NetworkX](https://github.com/networkx/networkx)
* [Louvain Community Detection](https://github.com/taynaud/python-louvain)
* [BotOrNot Python API](https://github.com/truthy/botornot-python) (_NOTE:_ adapted to use twitter_functions.py)