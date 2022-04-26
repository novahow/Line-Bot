import requests
import re
import random
import configparser
from bs4 import BeautifulSoup
from flask import Flask, request, abort
import json
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import *

app = Flask(__name__)

import os
import sys
from argparse import ArgumentParser
from flask_caching import Cache

from flask import Flask, request, abort, g
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
)

app = Flask(__name__)
cache = Cache()
cache.init_app(app=app, config={"CACHE_TYPE": "filesystem",'CACHE_DIR': '/tmp'})
# get channel_secret and channel_access_token from your environment variable
config = configparser.ConfigParser()
config.read("config.ini")

line_bot_api = LineBotApi(config['line_bot']['Channel_Access_Token'])
handler = WebhookHandler(config['line_bot']['Channel_Secret'])
API_TOKEN = config['hug']['API_TOKEN']
ASR_URL = "https://api-inference.huggingface.co/models/ydshieh/wav2vec2-large-xlsr-53-chinese-zh-cn-gpt"
API_URL = "https://api-inference.huggingface.co/models/wptoux/albert-chinese-large-qa"
ENG_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-mnli"
'''
output = query({
    "inputs": "Hi, I recently bought a device from your company but it is not working as advertised and I would like to get reimbursed!",
    "parameters": {"candidate_labels": ["labs, hobbies, university, courses, projects"]},
})
'''
HUG_HEAD = {"Authorization": f"Bearer {API_TOKEN}"}
CONTEXT = config['hug']['CONTEXT']
'''
    "inputs": {
		"question": "What's my name?",
		"context": "My name is Clara and I live in Berkeley."
	},
'''
def query(payload):
    payload['inputs']['context'] = CONTEXT
    # payload['wait_for_model'] = True
    response = requests.post(API_URL, headers=HUG_HEAD, json=payload)
    print('64', response.json())
    if 'error' in response.json().keys():
        return float(response.json()['estimated_time'])
    return response.json()['answer']
    
def equery(payload):
    payload['parameters'] = {"candidate_labels": ['labs', 'hobbies', 'university', 'courses', 'projects']}
    # payload['wait_for_model'] = True
    response = requests.post(ENG_URL, headers=HUG_HEAD, json=payload)
    if 'error' in response.json().keys():
        return float(response.json()['estimated_time'])
    return response.json()['labels'][:3]

def asrquery(filename):
    with open(filename, "rb") as f:
        data = f.read()
    response = requests.request("POST", ASR_URL, headers=HUG_HEAD, data=data)
    return json.loads(response.content.decode("utf-8"))

def show(tags, user):
    
            
    if tags == 'projects':
        line_bot_api.push_message(user, TextSendMessage(text=f'Here are my {tags}'))
        project_slide = json.load(open("./jsons/projects.json", "r"))
        proj_message = FlexSendMessage(alt_text='Projects', contents=project_slide)
        line_bot_api.push_message(user, proj_message)
        
    elif tags == 'hobbies':
        line_bot_api.push_message(user, TextSendMessage(text=f'My {tags} are table-tennis, basketball and movies/dramas'))
    elif tags == 'university':
        line_bot_api.push_message(user, TextSendMessage(text='I major in Computer Science and Information engineering in National Taiwan University.'))
    elif tags == 'courses':
        line_bot_api.push_message(user, TextSendMessage(text=f'ML-Related:\nDeep Learning for Computer Vision,\
                                                        \nApplied Deep Learning,\nMachine Learning\
                                                            \nFront/Backend-Related:\
                                                                \nWeb Programming'))
    else:
        line_bot_api.push_message(user, TextSendMessage(text=f'Machine Discovery and Social Network Mining Lab–Graph Mining Team\
            \nSpeech Processing and Machine Learning Lab'))

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def message_text(event):
    user = event.source.user_id
    message = event.message.text
    print(user, message)
    g = cache.get("g")
    
    if g == None:
        g = {}
    if 'state' not in g:
        g["state"] = {}
        
    if 'ans' not in g:
        g['ans'] = {}
    
    if user not in g["state"]:
        g["state"][user] = 0
        
    if user not in g['ans']:
        g['ans'][user] = []
        
    if message == 'END CHAT':
        g['state'][user] = 0
        g['ans'][user] = []
    elif message == 'help':
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f'END CHAT to restart\
                                                                            \nMode 1 is chinese QA, \nMode 2 is English QA(recommended)\
                                                                                \nMode 3 is ASR, you can record audio'))
        return
    elif g['state'][user] == 0:
        hint = TextSendMessage(
                text='please select mode.',
                quick_reply=QuickReply(
                    items=[
                        QuickReplyButton(
                            action=MessageAction(label="Mode 1(ChineseQA)", text="Mode 1(ChineseQA)")
                        ),
                        QuickReplyButton(
                            action=MessageAction(label="Mode 2(English)", text="Mode 2(English)")
                        ),
                        QuickReplyButton(
                            action=MessageAction(label="Mode 3", text="Mode 3")
                        ),
                    ]
                )
            )
        line_bot_api.reply_message(event.reply_token, hint)
        g['state'][user] = -1
    
    elif message == 'Mode 1(ChineseQA)':
        g['state'][user] = 1
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text='Your now in mode 1, please enter Chinese questions'))

    elif message == 'Mode 2(English)':
        g['state'][user] = 2
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text='Your now in mode 2, please enter English questions'))

    elif message == 'Mode 3':
        g['state'][user] = 3
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text='Your now in mode 3, please enjoy ASR'))

    elif g['state'][user] == 1:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text='等我一下喔...'))
        cache.set("g", g)
        data = query({"inputs": {
            "question": message,
        }})
        print(data, flush=True)
        if (type(data)) == float:
            line_bot_api.push_message(user, TextSendMessage(text=f'please wait for {data} seconds'))
            return
        # line_bot_api.push_message(user, TextSendMessage(text="Here is the result of sentence completion."))
        line_bot_api.push_message(user, TextSendMessage(text=data))

    elif g['state'][user] == 2:
        if message == 'NO' and len(g['ans'][user]):
            g['ans'][user] = []
            cache.set("g", g)
            return
        elif message == 'YES' and len(g['ans'][user]):
            g['ans'][user]['idx'] = min(g['ans'][user]['idx'] + 1, 2)
            dt = g['ans'][user]
            print(dt)
            show(dt['data'][dt['idx']], user)
            # line_bot_api.reply_message(event.reply_token, TextSendMessage(text=dt['data'][dt['idx']]))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='Please wait, inferencing...'))
            cache.set("g", g)
            data = equery({"inputs": message})
            if (type(data)) == float:
                line_bot_api.push_message(user, TextSendMessage(text=f'please wait for {data} seconds'))
                return
            g['ans'][user] = {'data': data, 'idx': 0}
            print('173', data, type(data), flush=True)
            dt = g['ans'][user]
            # line_bot_api.push_message(user, TextSendMessage(text="Here is the result of sentence completion."))
            show(dt['data'][dt['idx']], user)
            
        ques = TextSendMessage(
            text='Am I replying unrelated sentence?',
            quick_reply=QuickReply(
                items=[
                    QuickReplyButton(
                        action=MessageAction(label="YES", text="YES")
                    ),
                    QuickReplyButton(
                        action=MessageAction(label="NO", text="NO")
                    ),
                ]
            )
        )
        line_bot_api.push_message(user, ques)

    elif g['state'][user] == 3:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text='Record Audio'))
    
    else:
        g['state'][user] = 0
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text='Turning you back to stage 0...'))
    cache.set("g", g)
    
    


@handler.add(MessageEvent, message=AudioMessage)
def message_audio(event):
    user = event.source.user_id
    m_id = event.message.id
    print(user, m_id)
    g = cache.get("g")
    
    if g == None:
        g = {}
    if 'state' not in g:
        g["state"] = {}
        
    if 'ans' not in g:
        g['ans'] = {}
    
    if user not in g["state"]:
        g["state"][user] = 0
        
    if user not in g['ans']:
        g['ans'][user] = []
    
    if g['state'][user] != 3:
        return
    message_content = line_bot_api.get_message_content(m_id)
    with open('/tmp/aud.flac', 'wb') as fd:
        for chunk in message_content.iter_content():
            fd.write(chunk)

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text='Please wait, recognizing...'))
    output = asrquery('/tmp/aud.flac')
    if 'error' in output.keys():
        ws = float(output['estimated_time'])
        line_bot_api.push_message(user, messages=TextSendMessage(text=f'please wait for {ws} seconds'))
    else:
        line_bot_api.push_message(user, messages=TextSendMessage(text=output['text']))

if __name__ == "__main__":
    arg_parser = ArgumentParser(
        usage='Usage: python ' + __file__ + ' [--port <port>] [--help]'
    )
    arg_parser.add_argument('-p', '--port', default=8000, help='port')
    arg_parser.add_argument('-d', '--debug', default=False, help='debug')
    options = arg_parser.parse_args()

    app.run(debug=options.debug, port=options.port)