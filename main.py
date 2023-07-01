from modules.cloud_sql import *
from modules.for_reddit import *
from modules.status import *
from modules.sentience import *

import pytz
from random import *


class kingbot:
    def __init__(self):

        # Are we running in production or testing?
        self.production = is_production()

        # Load in Vizzy, Bobby, and Tyrion
        self.all_bots = makeBots()

        # Grab the quotes
        self.quotes = self.all_bots['vizzy_t_bot']['quotes']

        # Set default Reddit object to be Vizzy's Reddit
        self.reddit = self.all_bots['vizzy_t_bot']['r']

        # Initialize cloud database
        self.db = db()

        # Get the (string) of subs to follow
        self.sub_list = self.make_subs()

        # Turn them into a subreddit object
        self.subreddit = self.reddit.subreddit(self.sub_list)

        # Set the subreddit stream to comments and posts
        self.stream = praw.models.util.stream_generator(lambda **kwargs: submissions_and_comments(self.subreddit, **kwargs), skip_existing=False)

        # Grab the timezone
        self.tz = pytz.timezone(self.all_bots['vizzy_t_bot']['sentience']['timezone'])

        print("Configuration loaded successfully, Reddit initialized.")

    def make_comment(self,comment, response, bot):

        bot_reddit = self.all_bots[bot]['r']

        if isPost(comment):
            # Initialize the comment using the provided bot
            new_comment = bot_reddit.submission(id=comment.id)
        else:
            new_comment = bot_reddit.comment(id=comment.id)

        new_comment.reply(body=response)

        self.db.write_obj(comment.id, bot)

    def make_subs(self):
        """Multi-function, updated 2023-2-23
         Get a text-based list of the subreddits we should be watching based on the bot's location
         """

        if not self.production:

            return 'vizzy_t_test'

        else:
            for bot in self.all_bots:



                # Get a list of the subreddit types
                sub_categories = self.all_bots[bot]['subreddits'].keys()

                # Empty list for subreddits to crawl
                subs = []

                # Iterate through the subreddit categories
                for category in sub_categories:
                    # Skip vizzy_t_test if we're in production
                    if self.production and category == 'test':
                        pass
                    else:
                        for sub in self.all_bots[bot]['subreddits'][category]:
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

    def is_triggered(self, text, respondable_bots, sub):
        """Multi-function, updated 2023-2-23"""
        triggered = []



        for bot in self.all_bots:

            sublist = self.all_bots[bot]['subreddits']
            if self.production:
                subs = sublist['primary'] + sublist['other']
            else:
                subs = ['vizzy_t_test']

            if sub in subs:

                for word in self.all_bots[bot]['keywords']:
                    if word in text.lower() and bot not in triggered and bot in respondable_bots:
                        triggered.append(bot)

        return triggered

    def skip_checker(self, author, id):
        """
        Multi-function, updated 2023-2-23
        Check to see if we should skip this thing

        Makes sure we ignore deleted comments,
        Don't respond to our own comments
        And don't respond to comments we already responded to

        Anything in the skips list will be responded to, which is...backwards lol
        """

        skips = []



        for bot in self.all_bots:

            # Skip if the author is None (Someone deleted something)
            if author is None:
                pass

            # Skip if the author is the same as the bot
            elif author.lower() == bot.lower():
                pass

            # Skip if the comment ID is in the database already
            elif self.db.check_db(id, bot.lower()):
                pass

            # Otherwise, don't skip.
            else:
                skips.append(bot)

        return skips

    def get_details(self, object):
        """
        Multi-function, updated 2023-2-23
        Load the details of a post / comment, helpful for keeping bots from crashing on deleted things
        """

        # Get the author name
        author = object.author.name.lower()

        sub = object.subreddit

        # Get the author name
        author_original = object.author.name

        respondable_bots = self.skip_checker(author,object.id)

        if not respondable_bots:
            return False, False, False, False, False, False, False

        else:
            # Okay, the list "skip" has 1-2 bots in it that could possibly respond

            # If this is a comment, grab the comment body
            if isComment(object):

                text = object.body

            else:

                text = object.title + "\n" + object.selftext


            text = text.lower()

            permalink = f'https://www.reddit.com{object.permalink}'

            # Returns a list of triggered bots
            triggered = self.is_triggered(text, respondable_bots, sub)


            # This is only for Vizzy T
            funny = self.funny_business(text)

            return author, author_original, text, permalink, object.id, triggered, funny


    def sentience_checker(self,author, text, bot):
        """
        Updated 2023-2-23
        Check if a response should be sentient.  Takes multiple factors into consideration."""

        maesters = self.all_bots[bot]['maesters']
        ai = self.all_bots[bot]['sentience']

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

    def pull_quote(self, author, bot):
        """
        Updated 2023-2-23
        Sending a normal, random response"""

        # Seed the randomness
        seed()

        # Grab a quote
        response = choice(self.all_bots[bot]['quotes'])

        # Fill in user's username if applicable to this quote
        if "{}" in response:
            response = response.replace("{}", author)

        return response


    def thekingspeaks(self, redditObject, author, text, bot):
        """Primary function, processes everything"""
        tmp_name = self.all_bots[bot]['sentience']['sentient_name']

        xxx = self.sentience_checker(author.lower(), text, bot)

        # If we should be sentient...
        if xxx:

            # Get a sentient response and associated cost
            response, cost = get_sentient(redditObject, self.all_bots[bot])

            description = f"{tmp_name} made a sentient comment"

            self.db.usage_dump(author, author, f"{tmp_name} Sentience", text, response, redditObject.subreddit.display_name, redditObject.permalink, cost)

        else:

            # Generate the bot's response
            response = self.pull_quote(author, bot)
            cost = None
            description = f"{tmp_name} made a canon comment"

        # Check if Vizzy should show off his tapestries
        if 'tapestries' in response.lower():
            image_url = WOULDYOULIKETOSEETHETAPESTRIES(redditObject.author.name)
            response = f"[{response}]({image_url})"
            description += ", and showed off his tapestries!"
            self.db.usage_dump(author, author, "Vizzy T Sentience", text, response, redditObject.subreddit.display_name, redditObject.permalink, .2)

        else:
            description += "."


        self.make_comment(redditObject, response, bot)
        self.db.write_obj(redditObject.id, bot)

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
        for object in self.stream:
            try:

                # Grab info from the thing
                author, author_original, text, permalink, comment_id, is_triggered, deviant = self.get_details(object)

                # If there's no author, no text, and we're not triggered, skip it
                if not author and not text and not is_triggered:
                    pass

                else:
                    if deviant == "mustache" and 'vizzy_t_bot' in is_triggered:
                        print("Processing this post because it has a mustache and we're Vizzy T")

                        response = '[*...I know.*](https://thc-lab.net/static/i-know.gif)'

                        object.reply(body=response)

                        self.db.write_obj(comment_id, "vizzy_t_bot")

                    # Skip if we're not triggered
                    # This still works even though I changed it to a list
                    # Just move on if there's no triggers.
                    elif not is_triggered:
                        pass

                    # We are triggered and nothing else interesting should happen.
                    else:

                        for bot in is_triggered:

                            print("We're processing this post because no one told us not to!")

                            # Reply to the comment
                            # This function takes care of EVERYTHING
                            #
                            # Except for sending the webhook which is sent afterword
                            response, cost, description = self.thekingspeaks(object, author_original, text, bot)


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
