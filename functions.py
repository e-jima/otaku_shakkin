# -*- cofing: utf-8 -*-

import ast
import json
import datetime
import time
import re
import random
from PIL import Image, ImageDraw, ImageFont

import shutil
import traceback

def back_up_df():
    now = str(datetime.datetime.now()).replace("-", "").replace(":", "").replace(" ", "").split(".")[0]
    bk_name = "shakkin_list_"+now+".csv"
    shutil.copy("/Users/Shota/Documents/jupyter/otaku_shakkin_chang/shakkin_list/shakkin_list.csv",
                "/Users/Shota/Documents/jupyter/otaku_shakkin_chang/shakkin_list/backup/"+bk_name)
    
    
# ツイートするための画像を生成
def make_image(msg, use):
    base_image = Image.open("/Users/Shota/Documents/jupyter/otaku_shakkin_chang/images/base.png")
    draw = ImageDraw.Draw(base_image)
    f_size = 20
    b = (0, 0, 0)
    font = ImageFont.truetype("/Library/Fonts/ipaexg.ttf", f_size, encoding='utf-8')

    draw.text((10, 10), msg, b, font=font)

    now = str(datetime.datetime.now()).replace(" ", "").replace("-", "").replace(":", "").replace(".", "")

    if use == "all_list":
        filepath = "/Users/Shota/Documents/jupyter/otaku_shakkin_chang/images/all_list/"+now+".png"
    elif use == "diff_price":
        filepath = "/Users/Shota/Documents/jupyter/otaku_shakkin_chang/images/diff_price/"+now+".png"
    else:
        filepath = "/Users/Shota/Documents/"
    
    base_image.save(filepath)

    return filepath

def get_ymd(row):
    y = str(row.date).split(" ")[0].split("-")[0][2:]
    m = str(row.date).split(" ")[0].split("-")[1]
    d = str(row.date).split(" ")[0].split("-")[2]
    ymd = y+"/"+m+"/"+d
    return ymd
