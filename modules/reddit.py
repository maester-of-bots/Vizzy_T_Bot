
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


