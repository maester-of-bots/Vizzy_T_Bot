
from dotenv import load_dotenv
import os
import json
import linecache
import sys

import praw
from modules.az_vault import *

def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    filename = f.f_code.co_filename
    linecache.checkcache(filename)
    line = linecache.getline(filename, lineno, f.f_globals)
    data = ('EXCEPTION IN ({}, LINE {} "{}"): {}'.format(filename, lineno, line.strip(), exc_obj))
    return data

def submissions_and_comments(subreddit, **kwargs):
    results = []
    results.extend(subreddit.new(**kwargs))
    results.extend(subreddit.comments(**kwargs))
    results.sort(key=lambda post: post.created_utc, reverse=True)
    return results


def isPost(obj):
    return isinstance(obj,praw.models.Submission)

def isComment(obj):
    return isinstance(obj,praw.models.Comment)

def triggered(text):
    return "vizzy t" in text or "vissy t" in text


def makeBots():
    bots = {}

    for dir in os.listdir('bots'):
        file = os.path.join('bots', dir, f"{dir}.json")
        with open(file,'r') as lines:
            char_lines = lines.read()
            data = json.loads(char_lines)
        bots[dir] = data

    vault = keyvault()

    for bot in bots.keys():
        print(f"Loading {bot}")
        bots[bot]['r'] = praw.Reddit(
            client_id=vault.get_secret(bots[bot]['secrets'][0]),
            client_secret=vault.get_secret(bots[bot]['secrets'][1]),
            password=vault.get_secret(bots[bot]['secrets'][2]),
            user_agent=vault.get_secret(bots[bot]['secrets'][3]),
            username=vault.get_secret(bots[bot]['secrets'][4])
        )
        return bots


def checkStatus(bots):
    r = bots['vizzy_t_bot']['r']
    for bot in bots.keys():
        bot_obj = r.redditor(bot)
        if hasattr(bot_obj,'is_suspended'):
            print(f"{bot_obj.user.me()} is currently suspended.")
        else:
            print(f"{bot_obj.user.me()} is fine.")
