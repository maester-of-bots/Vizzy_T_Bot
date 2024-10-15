from modules.database import *
from modules.reddit import *
from modules.sentience import *

import pytz
from random import *
import socket
import requests

def get_ip():
    return requests.get('https://ipv4.canhazip.com').text.strip()


def resolve_name(name):
    results = socket.gethostbyname_ex(name)
    ips = []
    for thing in results:
        if thing == []:
            check = "thc"
        elif type(thing) == list:
            check = thing[0]
        elif type(thing) == str:
            check = thing
        else:
            check = "thc"
        if "thc" in check:
            pass
        else:
            ips.append(check)
    return ips[0]


def is_production():
    ip = get_ip()
    print(ip)
    if ip == resolve_name('thc-lab.net') or '172.190.216.87' in ip:
        print("We are in production")
        return True
    else:
        print("We are in Test")
        return False



class kingbot:
    def __init__(self):

        # Are we running in production or testing?
        self.production = is_production()
        self.vault = keyvault()

        # Load in Vizzy information
        file = os.path.join('data', "vizzy_t_bot.json")
        with open(file, 'r') as lines:
            char_lines = lines.read()
            self.data = json.loads(char_lines)

        self.data['r'] = praw.Reddit(
            client_id=self.vault.get_secret(self.data['secrets'][0]),
            client_secret=self.vault.get_secret(self.data['secrets'][1]),
            password=self.vault.get_secret(self.data['secrets'][2]),
            user_agent=self.vault.get_secret(self.data['secrets'][3]),
            username=self.vault.get_secret(self.data['secrets'][4])
        )


        # Grab the quotes
        self.quotes = self.data['quotes']

        # Set default Reddit object to be Vizzy's Reddit
        self.reddit = self.data['r']

        # Initialize cloud database
        self.db = db()

        # Get the (string) of subs to follow
        self.sub_list = self.make_subs()

        # Turn them into a subreddit object
        self.subreddit = self.reddit.subreddit(self.sub_list)

        # Set the subreddit stream to comments and posts
        self.stream = praw.models.util.stream_generator(lambda **kwargs: submissions_and_comments(self.subreddit, **kwargs), skip_existing=False)

        # Grab the timezone
        self.tz = pytz.timezone(self.data['sentience']['timezone'])

        print("Configuration loaded successfully, Reddit initialized.")


    def make_comment(self,comment, response):

        bot_reddit = self.data['r']

        if isPost(comment):
            # Initialize the comment using the provided bot
            new_comment = bot_reddit.submission(id=comment.id)
        else:
            new_comment = bot_reddit.comment(id=comment.id)

        new_comment.reply(body=response)

        self.db.write_obj(comment.id, "vizzy_t_bot")

    def make_subs(self):
        if not self.production:
            return 'vizzy_t_test'
        else:
            # Get a list of the subreddit types
            sub_categories = self.data['subreddits'].keys()

            # Empty list for subreddits to crawl
            subs = []

            # Iterate through the subreddit categories
            for category in sub_categories:
                # Skip vizzy_t_test if we're in production
                if self.production and category == 'test':
                    pass
                else:
                    for sub in self.data['subreddits'][category]:
                        if sub not in subs:
                            subs.append(sub)
            sublist = '+'.join(subs)
            return sublist


    def funny_business(self,text):
        """ Easter Eggs go here. """

        # Woohoo Hot fuzz
        if "got a mustache" in text:
            return "mustache"

        elif "the whore is pregnant" in text:
            return "whore"

        else:
            return "None"

    def is_triggered(self, text, sub):

        sublist = self.data['subreddits']
        if self.production:
            subs = sublist['primary'] + sublist['other']
        else:
            subs = ['vizzy_t_test']

        if sub in subs:
            for word in self.data['keywords']:
                if word in text.lower():
                    return True

        return False

    def skip_checker(self, author, id):

        # Skip if the author is None (Someone deleted something)
        if author is None:
            return True

        # Skip if the author is the same as the bot
        elif author.lower() == 'vizzy_t_bot':
            return True

        # Skip if the comment ID is in the database already
        elif self.db.check_db(id, 'vizzy_t_bot'):
            return True

        # Otherwise, don't skip.
        else:
            return False

    def get_details(self, object):
        """
        Multi-function, updated 2023-2-23
        Load the details of a post / comment, helpful for keeping data from crashing on deleted things
        """

        # Get the author name
        author = object.author.name.lower()

        sub = object.subreddit

        # Get the author name
        author_original = object.author.name

        should_skip = self.skip_checker(author,object.id)

        if should_skip:
            return False, False, False, False, False, False, False

        else:
            if isComment(object):
                text = object.body.lower()

            else:
                text = (object.title + "\n" + object.selftext).lower()

            permalink = f'https://www.reddit.com{object.permalink}'

            # Returns a list of triggered data
            triggered = self.is_triggered(text, sub)

            # This is only for Vizzy T
            funny = self.funny_business(text)

            return author, author_original, text, permalink, object.id, triggered, funny


    def sentience_checker(self,author, text):
        """
        Updated 2023-2-23
        Check if a response should be sentient.  Takes multiple factors into consideration."""

        maesters = self.data['maesters']
        ai = self.data['sentience']

        # If Sentience is disabled in the config, we won't be sentient.  Still allows for Maesters.
        if ai['enabled'] is False and author not in maesters:
            response = False

        # If the author is in the sentience whitelist, go ahead and be sentient.
        elif (author in ai['sentience_whitelist']
              or author in maesters) and text.count("*") >= 2:
            response = True

        # If the sentience limiter is enabled, check and see if it's the appropriate time.
        elif ai['enabled'] is True and ai['sentience_limiter'] is True:

            # Get current timestuff
            ts = datetime.now(self.tz)
            h = ts.hour
            m = ts.minute

            # Do calculations
            waking_up = (h == ai['wakeup'][0] and m >= ai['wakeup'][1])
            going_to_sleep = (h == ai['sleep'][0] and m <= ai['sleep'][1])

            # This is a little better, but still static in the sense that it won't work unless it's 11PM-12AM.
            # Check if it's between the specified times in config and if Vizzy should be sentient or not
            if (waking_up) or (going_to_sleep):
                response = True

            else:
                response = False

        else:
            response = False

        return response

    def pull_quote(self, author):
        """
        Updated 2023-2-23
        Sending a normal, random response"""

        # Seed the randomness
        seed()

        # Grab a quote
        response = choice(self.data['quotes'])

        # Fill in user's username if applicable to this quote
        if "{}" in response:
            response = response.replace("{}", author)

        return response


    def thekingspeaks(self, redditObject, author, text):
        """Primary function, processes everything"""

        shouldBeSentient = self.sentience_checker(author.lower(), text)

        # If we should be sentient...
        if shouldBeSentient:

            # Get a sentient response and associated cost
            response, cost = get_sentient(redditObject, self.data)

            description = "Vizzy T made a sentient comment"

            self.db.usage_dump(author, author, "Vizzy T Sentience", text, response, redditObject.subreddit.display_name, redditObject.permalink, cost)

        # Otherwise, get a random quote.
        else:
            # Generate the bot's response
            response = self.pull_quote(author)
            cost = None
            description = "Vizzy T made a canon comment"

        # Check if Vizzy should show off his tapestries
        if 'tapestries' in response.lower():
            image_url = WOULDYOULIKETOSEETHETAPESTRIES(redditObject.author.name)
            response = f"[{response}]({image_url})"
            description += ", and showed off his tapestries!"
            self.db.usage_dump(author, author, "Vizzy T Sentience", text, response, redditObject.subreddit.display_name, redditObject.permalink, .2)

        else:
            description += "."


        self.make_comment(redditObject, response)
        self.db.write_obj(redditObject.id)

        print("Dumped comment!")

        return response, cost, description

    def run(self):
        """
        Main function, iterates through comments and responds as needed

        if isComment(obj):
            if obj.submission.link_flair_text == "Book Only":
                pass
        elif isPost(obj):
            if obj.link_flair_text == "Book Only":
                pass
        """

        # Iterate through all the posts / comments
        for reddit_object in self.stream:
            try:

                # Grab info from the thing
                author, author_original, text, permalink, comment_id, is_triggered, deviant = self.get_details(reddit_object)

                if not is_triggered:
                    continue

                elif not author and not text:
                    continue

                else:
                    if deviant == "mustache" and is_triggered:
                        print("Processing this post because it has a mustache and we're Vizzy T")

                        response = '[*...I know.*](https://thc-lab.net/static/i-know.gif)'

                        reddit_object.reply(body=response)

                        self.db.write_obj(comment_id, "vizzy_t_bot")

                    # We are triggered and nothing else interesting should happen.
                    else:

                        print(f"We're processing {comment_id} because no one told us not to!")

                        # Reply to the comment
                        # This function takes care of EVERYTHING
                        #
                        # Except for sending the webhook which is sent afterword
                        response, cost, description = self.thekingspeaks(reddit_object, author_original, text)
                        print(response)


            except Exception as e:

                try:

                    # Send errors to Discord
                    print(e)
                except:
                    print("Fuckin broke again")
                    pass


# GODS BE GOOD
while True:
    try:
        kingbot = kingbot().run()
    except Exception as e:
        print(e)
        pass
