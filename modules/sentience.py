import os
import openai
import praw
from modules.az_vault import *
import requests

import requests
import json

from datetime import *

vault = keyvault()

endpoint_ID = vault.get_secret('THCEndpointID')
endpoint_secret = vault.get_secret('THCEndpointSecret')
endpoint_url = vault.get_secret('THCEndpointURL')




def isComment(obj):
    return isinstance(obj,praw.models.Comment)


def render_image_azure(username):
    data = {
        "prompt": f"Regal tapestries decorated in the style of their King's online username, {username}",
        "size": "1024x1024",
        "quality": "hd",
        "style": "vivid",
        "user": "Vizzy T",
        endpoint_ID: endpoint_secret
      }

    headers = {'Content-Type': 'application/json'}

    data = json.dumps(data)
    response = requests.post(endpoint_url, data=data, headers=headers)
    final = response.json()
    # revised_prompt = final['revised_prompt']
    url = final['url']
    return url


def WOULDYOULIKETOSEETHETAPESTRIES(prompt):
    image_resp = render_image_azure(prompt)

    url = image_resp['data'][0]['url']

    submit_url = 'https://thc-lab.net/art.html'

    timestamp = datetime.now().timestamp()

    filename = f"Tapestries_{timestamp}.jpeg"

    payload = {
        'code': endpoint_secret,
        'url': url,
        'filename': filename,
        'subdir': 'tapestries'
    }

    r = requests.post(submit_url, data=payload)
    return r.text


def get_sentient(comment, bot):

    # Craft the initial base
    base_list = bot['sentience']['prompt']

    base = "\n".join(base_list)

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

