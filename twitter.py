# -*- coding: utf-8 -*-

# Python 3.5.0

# twitter に関する関数

import sys
sys.path.append("./secret")
import secret

CK = secret.CK
CS = secret.CS
AT = secret.AT
AS = secret.AS

import pandas as pd
import requests_oauthlib
import ast
import json
import requests
import datetime
import time
import re
import random
from PIL import Image, ImageDraw, ImageFont

import shutil
import traceback

auth = requests_oauthlib.OAuth1(CK, CS, AT, AS)

def get_followers():
    url = "https://api.twitter.com/1.1/followers/list.json"
    req = requests.get(url, auth=auth)
    
    if req.status_code != 200:
        return dict()
    
    raw_data = json.loads(req.text)
    followers = raw_data["users"]
    res = {}
    for f in followers:
        res[f["screen_name"]] = f["id"]
    return res

def get_media_ids(images):
    url = "https://upload.twitter.com/1.1/media/upload.json"
    
    media_ids = []
    for im in images:
        file = {"media": im}
        req = requests.post(url, auth=auth, files=file)
    
        if req.status_code != 200:
            return []
        
        media_ids.append(str(json.loads(req.text)["media_id"]))
    return media_ids


def get_timeline(followers):
    data = {"follow": followers.values()}
    url = "https://stream.twitter.com/1.1/statuses/filter.json"
    req = requests.post(url, auth=auth, stream=True, data=data)

    return req
            
    
# req 結果自体で返す
def get_tweet_by_id(tw_id):
    url = "https://api.twitter.com/1.1/statuses/show.json?id="+str(tw_id)
    req = requests.get(url, auth=auth)
    
    return req
    
    
def post_tweet(text):
    url = "https://api.twitter.com/1.1/statuses/update.json"
    data = {"status": text+str(datetime.datetime.now())}
    req = requests.post(url, auth=auth, data=data)

    return req
    
    
def post_tweet_reply(user, tweet_id, text):
    url = "https://api.twitter.com/1.1/statuses/update.json"
    data = {"status": "@"+user+" "+text, "in_reply_to_status_id": tweet_id}
    req = requests.post(url, auth=auth, data=data)
    
    return req
    
    
def post_tweet_with_media(media_ids, text):
    media_ids = ",".join(media_ids)
    url = "https://api.twitter.com/1.1/statuses/update.json"
    data = {"status": text, "media_ids": media_ids}
    req = requests.post(url, auth=auth, data=data)
    
    return req


def post_tweet_reply_with_media(media_ids, user, tweet_id, text):
    media_ids = ",".join(media_ids)
    url = "https://api.twitter.com/1.1/statuses/update.json"
    data = {"status": "@"+user+" "+text, "media_ids": media_ids, "in_reply_to_status_id": tweet_id}
    req = requests.post(url, auth=auth, data=data)
    
    return req


# 返り値は raw_data を dict にしたやつ
def get_user_timeline(user_id, count):
    url = "https://api.twitter.com/1.1/statuses/user_timeline.json?screen_name="+user_id+"&count="+str(count)
    req = requests.get(url, auth=auth)
    
    if req.status_code != 200:
        return []
    
    return json.loads(req.content.decode("utf-8"))
