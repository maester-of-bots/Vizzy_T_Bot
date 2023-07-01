from dotenv import load_dotenv
import os
import openai
import praw

import requests

from datetime import *

load_dotenv()
openai.api_key = os.getenv('sentient_v')

# Fastest

openai_models = {
    "ada": {
        "1000": 0.0004,
        "1": 0.0004/1000,
        "name": 'text-ada-001'
    },
    "babbage": {
        "1000": 0.0005,
        "1": 0.0005/1000,
        "name": 'text-babbage-001'
    },
    "curie": {
        "1000": 0.0020,
        "1": 0.0020/1000,
        "name": 'text-curie-001'
    },
    "davinci": {
        "1000": 0.0200,
        "1": 0.0200/1000,
        "name": 'text-davinci-002'
    },
}

def isComment(obj):
    return isinstance(obj,praw.models.Comment)


def tokenCalculator(comment, model):
    """ Return the amount of tokens this comment would represent"""
    spaces = comment.count(' ')
    words = len(comment)
    chars = words - spaces
    tokens = chars / 4

    # Dollar amounts
    costs = {
        "ada": tokens * openai_models["ada"]["1"],
        "babbage": tokens * openai_models["babbage"]["1"],
        "curie": tokens * openai_models["curie"]["1"],
        "davinci": tokens * openai_models["davinci"]["1"],
    }

    return tokens, costs[model]


def WOULDYOULIKETOSEETHETAPESTRIES(prompt):
    full_prompt = f"Regal tapestries adorned with {prompt}"
    image_resp = openai.Image.create(prompt=full_prompt, n=1, size='1024x1024')

    url = image_resp['data'][0]['url']

    submit_url = 'https://thc-lab.net/art.html'

    timestamp = datetime.now().timestamp()

    filename = f"Tapestries_{timestamp}.jpeg"

    payload = {
        'code': 'fuck you you fucking fuck',
        'url': url,
        'filename': filename,
        'subdir': 'tapestries'
    }

    r = requests.post(submit_url, data=payload)
    return r.text


def get_sentient(comment, bot):

    # Craft the initial base
    base_list = bot['sentience']['prompt']

    base = f"""The following is a conversation with Viserys I Targaryen, a character from the show "House of the Dragon", or Vizzy T.
    .
    
    .
    """

    base = "\n".join(base_list)

    if "bobby-b-bot" in comment.author.name.lower() and bot == 'vizzy_t_bot':
        base += f'\nVizzy T will speak to {comment.author.name} as a king would speak to a member of his court, and commands respect from them.\n'
    elif "vizzy_t_bot" in comment.author.name.lower() and bot == 'bobby-b-bot_':
        base += "\nVizzy T recognizes bobby-b-bot_ as King Robert Baratheon, a future King of Westeros."
    else:
        base += f'\nBobby B will speak to {comment.author.name} as a king would speak to a member of his court, and commands respect from them.\n'

    reading = True
    current = comment
    levels = 0
    entries = []

    stop = []


    while reading:
        try:
            author = current.author.name.lower()
            if author == 'vizzy_t_bot':
                author = "Vizzy T"
            elif author == 'bobby-b-bot_':
                author = "Bobby B"

            if f'{author}: ' not in stop:
                stop.append(f'{author}: ')

            try:
                msg = current.body.replace('^(This response generated with OpenAI) [DaVinci]','')
            except:
                reading = False

            entry = f"{str(author)}: {msg}\n"
            entries.append(entry)

            levels += 1

            if levels == 4:
                reading = False
            else:
                try:
                    current = current.parent()
                    if isComment(current):
                        continue
                    else:
                        reading = False
                except:
                    reading = False
        except:
            reading = False

    entries.reverse()

    for entry in entries:
        base += entry

    if bot['bot_name'] == 'vizzy_t_bot':
        shortname = "Vizzy T"
    elif bot['bot_name'] == "bobby-b-bot_":
        shortname = "Bobby B"
    else:
        shortname = "Vizzy T"

    base += f"{shortname}: "

    print("Making sentience")

    presence_penalty = .8
    max_tokens = 500

    # Generate the raw response data
    data = openai.Completion.create(engine='text-davinci-003',
                                    prompt=base,
                                    max_tokens=max_tokens,
                                    presence_penalty=presence_penalty,
                                    temperature=.9,
                                    stop=stop)

    # Grab the response out of the data dict
    response = data['choices'][0]['text']

    # Parse out the line we need
    parsed = response.replace('User', comment.author.name).strip().replace(f"{shortname}:","").replace(f"{shortname.lower()}:","").strip()

    try:
        if str(comment.parent().body) == parsed:
            return False, False
        else:
            # Get token cost, and round it to six places.
            cost = data['usage']['total_tokens']

            return parsed, cost
    except:
        print("Ugh")
        # Get token cost, and round it to six places.
        cost = data['usage']['total_tokens']

        return parsed, cost

