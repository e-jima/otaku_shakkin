# -*- coding: utf-8 -*-

from functions import *
from twitter import *
from Mayu_bot import *


import pandas as pd
import json
import ast
import datetime
import time
import json
import re
import random
import traceback
import urllib
import re

from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta


# 借金リストのパス
path = "../shakkin_list/shakkin_list.csv"
bot_id = "otaku_shakkin"

class Mayu:
    
    def __init__(self, raw_data):
        
        # raw_data も保持しとく
        self.raw_data = raw_data

        # 借金データの読み込み
        self.df = pd.read_csv(path, encoding="utf-8", parse_dates=[0])
        self.columns = self.df.columns
        
        # ツイート ID
        self.tw_id = raw_data["id_str"]
        # 作成日時
        self.tw_date = datetime.datetime.strptime(raw_data["created_at"], '%a %b %d %H:%M:%S +0000 %Y')+datetime.timedelta(hours=9)
        # 誰からのリプライか
        self.from_id = raw_data["user"]["screen_name"]
        # ユーザネーム
        self.user_name = raw_data["user"]["name"]
        
        # bot へのリプライか？ デフォルトは False
        self.is_reply = False
        
        self.member = []
        for u in raw_data["entities"]["user_mentions"]:
            user_id = u["screen_name"]
            #  @ に bot_id が含まれていたら is_reply を True に
            if user_id == bot_id:
                self.is_reply = True
            else:
                # bot 以外のメンション相手は member へ
                self.member.append(user_id)
                
        self.is_conversation = False
        # bot がリプライ相手に含まれてない会話には参加しない
        if (not self.is_reply) and len(self.member) > 0:
            self.is_conversation = True
            
                
        # @ID を全部抜いたテキストを抽出、空白も除去
        self.text = raw_data["text"].replace("@"+bot_id, "")
        for i in self.member:
            self.text = self.text.replace("@"+i, "")
        self.text = re.sub(r'\s', "", self.text)
        
        # リツイートされて回ってきたツイートかどうか
        self.is_retweet = self.text.startswith("RT @")
        
        # 逆登録かどうか (逆登録は、最後に「逆」しか受け付けないことにする)
        self.is_reverse = (self.text[-1:] == "逆")
        # 逆登録のときは、最後の「逆」を取り除く
        if self.is_reverse:
            self.text = self.text[:-1]
            
    # 4文字のハッシュ
    def get_random_hash(self):
        s = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        h = ""
        for i in range(4):
            h = h+random.choice(s)
        # すでにあるやつと被ったらやり直し
        while h in list(self.df["id"]):
            h = ""
            for i in range(4):
                h = h+random.choice(s)
        return h
    
    
    # エラー時
    def error_mes(self):
        mes = "エラーが起きました…\n考えられる原因:\n・文字数オーバー\n・検索対象ツイートが削除された\nなど…"
        post_tweet_reply(self.from_id, self.tw_id, mes)
        
        return True
        
    
    
    # 借金登録
    def add_debt(self):
        
        if len(self.text) > 100:
            self.error_mes()
            return True
        
        if "ID:" in self.text:
            mes = "登録できない文字列が含まれているみたいです…"
            post_tweet_reply(self.from_id, self.tw_id, mes)
            return True
            
        
        for mem in self.member:
            lender_id = self.from_id
            borrower_id = mem
            if self.is_reverse:
                if len(self.member) == 1:
                    tmp = lender_id
                    lender_id = borrower_id
                    borrower_id = tmp
                # 複数人への逆登録は弾く
                else:
                    mes = "意図した登録にならないかもしれません…\n逆登録の場合は一人に対してしかできません。"
                    post_tweet_reply(self.from_id, self.tw_id, mes)
                    return True

            # バックアップ
            back_up_df()

            price = self.text.split("円")[0]
            if price.isdigit():
                price = "{:,}".format(int(price))
            content = self.text.split("円")[-1]
            if price == "":
                price = "nullですよぉ"
            if content == "":
                content = "nullですよぉ"
            rh = self.get_random_hash()
            if self.is_reverse:
                mes = "登録完了です！(逆登録)\n"
            else:
                mes = "登録完了です！\n"
            mes = mes+"@"+lender_id+" から "+"@"+borrower_id+" へ\n"+price+"円: "+content+"\n#オタク借金\nID: "+rh
            post_tweet_reply(self.from_id, self.tw_id, mes)

            # 返信ツイートの ID を取得
            reply_id = get_user_timeline("otaku_shakkin", 10)[0]["id_str"]
            # columns = [u'date', u'tweet_id', u'from_id', u'reply_id', u'id', u'price', u'content', u'lender', u'borrower', u'done']
            row = pd.DataFrame([[self.tw_date, self.tw_id, "@"+self.from_id, reply_id, rh, price, content, "@"+lender_id, "@"+borrower_id, 0]], columns=self.columns)
            self.df = self.df.append(row, ignore_index=True)

        self.df.to_csv(path, encoding="utf-8", index=False)


        
        
        
    # 借金済み
    def debt_done(self):
        
        # いきなり"済み"って送られてきたパターン
        if self.raw_data["in_reply_to_status_id_str"] == None:
            self.random_reply()
            return False
         
        # リプライ元のツイート取得
        tw_in_rep_req = get_tweet_by_id(self.raw_data["in_reply_to_status_id_str"])
        
        # リプライ元のツイートが取得できなかった場合
        if tw_in_rep_req.status_code != 200:
            self.random_reply()
            return False
        
        # リプライ元のツイート取得
        tw_in_rep = json.loads(tw_in_rep_req.content.decode("utf-8"))
        
        # bot のツイートに対するリプライで、かつ bot の登録ツイートか?
        if (tw_in_rep["user"]["screen_name"] != bot_id) or ("ID: " not in tw_in_rep["text"]):
            self.random_reply()
            return False
        
        # バックアップ
        back_up_df()

        done_id = tw_in_rep["text"].split("ID: ")[-1]
        update_row = self.df[self.df.id == done_id]
        
        # その借金の貸し借りに関わっている人しか完了できない
        if list(update_row["borrower"] == "@"+self.from_id)[0] or list(update_row["lender"] == "@"+self.from_id)[0]:
            self.df.loc[self.df.id == done_id, "done"] = 1
            self.df.to_csv(path, encoding="utf-8", index=False)
            if update_row["borrower"].item() == "@"+self.from_id:
                mes = update_row["lender"].item()+" 更新完了です！"
            else:
                mes = update_row["borrower"].item()+" 更新完了です！"
                
            post_tweet_reply(self.from_id, self.tw_id, mes)
            return True
        
        else:
            mes = "あなたはこの借金に関わってませんねぇ…？"
            post_tweet_reply(self.from_id, selt.tw_id, mes)
            return True
        
        
    # 借金全部済みのやつ   
    def debt_all_done(self):

        # いきなり"全部済み"って送られてきたパターン
        if self.raw_data["in_reply_to_status_id_str"] == None:
            self.random_reply()
            return False
         
        # リプライ元のツイート取得
        tw_in_rep_req = get_tweet_by_id(self.raw_data["in_reply_to_status_id_str"])
        
        # リプライ元のツイートが取得できなかった場合
        if tw_in_rep_req.status_code != 200:
            self.random_reply()
            return False
        
        # リプライ元のツイート取得
        tw_in_rep = json.loads(tw_in_rep_req.content.decode("utf-8"))
        
        # bot のツイートに対するリプライで、かつ bot の登録ツイートか?
        if (tw_in_rep["user"]["screen_name"] != bot_id) or ("ID: " not in tw_in_rep["text"]):
            self.random_reply()
            return False
                
        done_ids = tw_in_rep["text"].split("ID: ")[-1].split(" ")[0].split("/")[:-1]
        if len(done_ids) == 0:
            mes = "更新できるものはありませんでした…"
            post_tweet_reply(self.from_id, self.tw_id, mes)
            return True
        
        # バックアップ
        back_up_df()
        
        for done_id in done_ids:

            update_row = self.df[self.df.id==done_id]
            
            # お相手さん
            if update_row["borrower"].item() == "@"+self.from_id:
                me = update_row["borrower"].item()
                man = update_row["lender"].item()
            else:
                me = update_row["lender"].item()
                man = update_row["borrower"].item()
                
            reply_id = str(list(update_row.reply_id)[0])

            
            if "@"+self.from_id != man and "@"+self.from_id != me:
                mes = "あなたはこの借金に関わってませんねぇ…？"
                post_tweet_reply(self.from_id, selt.tw_id, mes)
                return True
                
            self.df.loc[self.df.id == done_id, "done"] = 1
            post_tweet_reply(bot_id, reply_id, "これは更新されました♡\n"+str(datetime.datetime.now()))

        self.df.to_csv(path, encoding="utf-8", index=False)
        mes = man+" 全て更新完了しました♡"
        post_tweet_reply(self.from_id, self.tw_id, mes)
        return True
    
    
    # 一覧表示
    def get_all_list(self):
        from_id = "@"+self.from_id
        df = self.df.copy()

        lend_df = df[df["lender"]== from_id]
        lend_df = lend_df[lend_df["done"]==0.0]

        lend_price = 0
        lend_msg = "  "
        for i in range(len(lend_df)):
            row = lend_df.iloc[i]
            
            # 日付
            ymd = get_ymd(row)
            
            lend_msg = lend_msg + ymd + "  "+row.price+"円 ( "+ row.content+" ): "+ row.borrower+" へ\n  "
            
            price = row.price.replace(",", "")
            if price.isdigit():
                lend_price = lend_price + int(price)

        if len(lend_df) == 0:
            lend_msg = "  なし\n"


        msg = from_id+ " が貸してる分 (総額: "+"{:,}".format(lend_price)+"円)\n"+lend_msg+"\n"


        borrow_df = df[df["borrower"] == from_id]
        borrow_df = borrow_df[borrow_df["done"] == 0.0]

        borrow_price = 0
        borrow_msg = "  "

        for i in range(len(borrow_df)):
            row = borrow_df.iloc[i]
            
            # 日付
            ymd = get_ymd(row)
            
            borrow_msg =borrow_msg + ymd + "  " + row.price+"円 ( "+ row.content+" ): "+ row.lender+" から\n  "
            price = row.price.replace(",", "")
            if price.isdigit():
                borrow_price = borrow_price + int(price)

        if len(borrow_df) == 0:
            borrow_msg = "  なし\n"

        msg = msg + from_id + " が借りてる分 (総額: "+"{:,}".format(borrow_price)+"円)\n"+borrow_msg+"\n"
        msg = msg + "※ 総額は計算できるもののみの和を表示"
        
        return msg
    
    
    # 差額を計算
    def calc_diff_price(self, man):

        from_id = "@"+self.from_id
        df = self.df.copy()
        man = "@"+man

        target_id = ""

        lend_bool = []
        borrow_bool = []
        for i, j, k in zip(list(df["lender"] == from_id), list(df["borrower"] == man), list(df["done"] == 0.0)):
            lend_bool.append(i & j & k)

        for i, j, k in zip(list(df["lender"] == man), list(df["borrower"] == from_id), list(df["done"] == 0.0)):
            borrow_bool.append(i & j & k)

        lend_df = df[lend_bool]
        borrow_df = df[borrow_bool]

        unk = "  "

        lend_price = 0
        lend_msg = "  "
        for i in range(len(lend_df)):
            row = lend_df.iloc[i]
            ymd = get_ymd(row)
            price = row.price
            content = row.content
            target_id = target_id+row.id+"/"

            if price.replace(",", "").isdigit():
                lend_price = lend_price + int(price.replace(",", ""))
                lend_msg =lend_msg + ymd + "  "+price+"円 ( "+ content+" )\n  "
            else:
                unk = unk + price+ "円 ( "+content+" ), "+man+" へ\n  "

        if lend_price == 0:
            lend_msg = "  なし\n"

        msg = man+ " に貸してる分 (総額: "+("{:,}".format(lend_price))+"円)\n"+lend_msg+"\n"

        borrow_price = 0
        borrow_msg = "  "

        for i in range(len(borrow_df)):
            row = borrow_df.iloc[i]
            ymd = get_ymd(row)
            price = row.price
            content = row.content
            target_id = target_id+row.id+"/"

            if price.replace(",", "").isdigit():
                borrow_price = borrow_price + int(price.replace(",", ""))
                borrow_msg =borrow_msg + ymd +"  " + price+"円 ( "+ content+" )\n  "
            else:
                unk = unk + price+ "円 ( "+content+" ), "+man+" から\n  "

        if borrow_price == 0:
            borrow_msg = "  なし\n"

        msg = msg + man+" から借りてる分 (総額: "+("{:,}".format(borrow_price))+"円)\n"+borrow_msg+"\n"
        msg = msg + "※ 総額、差額は計算できるもののみを利用"

        if len(unk) > 2:
            msg = msg + "\n\n金額不明:\n"+unk

        diff_price = lend_price-borrow_price
        if diff_price == 0:
            msg = "差額はゼロです♡\n\n"+msg
        if diff_price > 0:
            msg = "差額は　"+str(diff_price)+"円です。\n"+from_id+" が "+man+" から返してもらってくださいね♡\n\n"+msg
        if diff_price < 0:
            msg = "差額は "+str(-diff_price)+"円です。\n"+from_id+" が "+man+" へ返してくださいね♡\n\n"+msg

        return msg, target_id
    
    
    # ワード検索
    def search_word(self, w):
        df = self.df.copy()
        from_id = "@"+self.from_id

        search_df = df[list(map(lambda x: (x[0] | x[1]) & x[2] & (w in x[3]), 
                           zip(list(df.lender==from_id), list(df.borrower==from_id), list(df.done==0.0), list(df.content))))]

        mes = ""
        for i in range(len(search_df)):
            tmp = search_df.iloc[i]
            mes = mes + "https://twitter.com/"+tmp.from_id.replace("@", "")+"/status/"+str(tmp.tweet_id)+"\n"
            
        if mes != "":
            mes = "これですかぁ？\n" + mes
        else:
            mes = "指定の検索ワードでの登録は見つかりませんでした…"
        
        post_tweet_reply(self.from_id, self.tw_id, mes)
        
        return True
    
    # 一覧の画像を返す
    def return_all_list(self, msg):
        f = []
        if len(msg.split("\n")) > 45:
            half = "\n".join(msg.split("\n")[:44])+"\n\n(続)"
            a = open(make_image(half, "all_list"), "rb")
            f.append(a)
            half = "\n".join(msg.split("\n")[44:])
            b = open(make_image(half, "all_list"), "rb")
            f.append(b)
        else:
            a = open(make_image(msg, "all_list"), "rb")
            f.append(a)
            b = open(make_image(msg, "all_list"), "rb")
            
        images = f
        mes = "どうぞ♡"
        media_ids = get_media_ids(images)
        a.close()
        b.close()
        post_tweet_reply_with_media(media_ids, self.from_id, self.tw_id, mes)
        
        return True
    
    
    # 差額結果を返す
    def return_diff_price(self, member):
        # all_id は、差額対象ツイ全部のID
        msg, all_id = self.calc_diff_price(member)
        if all_id == "":
            all_id = "なし"
        f = open(make_image(msg, "diff_price"), "rb")
        images = [f]
        mes = ".@"+member+" さんとの差額です♡\nID: "+all_id
        media_ids = get_media_ids(images)
        f.close()
        
        if len(mes) > 130:
            self.error_mes()
        else:
            post_tweet_reply_with_media(media_ids, self.from_id, self.tw_id, mes)
        
        return True
    
    # イベノからイベント詳細を探してくる
    def search_events(self, w):
        root_url = "https://www.eventernote.com/events/search?keyword="

        keyword = w
        # 空白系を + に変換
        keyword = "+".join(keyword.split())
        # ascii に変換
        keyword = urllib.parse.quote(keyword, safe="+")

        now= datetime.datetime.now()
        year_month = [now+relativedelta(months=i) for i in range(6)]
        weekday = ["月", "火", "水", "木", "金", "土", "日"]

        lines = "===\n"
        for ym in year_month:
            lines += str(ym.year)+"年"+str(ym.month)+"月\n\n"
            url = root_url+keyword+"&year="+str(ym.year)+"&month="+str(ym.month)+"&day=&area_id=&prefecture_id="

            req = urllib.request.Request(url)
            page = urllib.request.urlopen(req)
            soup = BeautifulSoup(page)

            events = soup.find_all("div", "event")
            dates = [re.findall(r'\">(.+?)<', str(x))[0].replace(" (", "") for x in soup.find_all("p", re.compile(r'day\d'))]

            for d, e in zip(reversed(dates), reversed(events)):
                d = datetime.datetime.strptime(d, "%Y-%m-%d")
                title = re.findall(r'\">(.+?)<', str(e.find_all("h4")))
                place_time = re.findall(r'\">(.+?)<', str(e.find_all("div", "place")))
                lines += "  "+str(d.month)+"."+str(d.day)+"("+weekday[d.weekday()]+") @ "+" ( ".join(place_time)+" )\n"
                lines += "    "+title[0]+"\n\n"
            if len(events) == 0:
                lines += "    なし\n\n"
            lines += "===\n"

            
        f = []
        if len(lines.split("\n")) > 45:
            half = "\n".join(lines.split("\n")[:44])+"\n\n(続)"
            a = open(make_image(half, "eveno"), "rb")
            f.append(a)
            half = "\n".join(lines.split("\n")[44:])
            b = open(make_image(half, "eveno"), "rb")
            f.append(b)
        else:
            a = open(make_image(lines, "eveno"), "rb")
            f.append(a)
            b = open(make_image(lines, "eveno"), "rb")
            
        images = f
        mes = "どうぞ♡"
        media_ids = get_media_ids(images)
        a.close()
        b.close()
        post_tweet_reply_with_media(media_ids, self.from_id, self.tw_id, mes)
        
        return True
        
    
    # あいさつ
    def greet(self):
        mes = ""
        if "おは" in self.text and len(self.text) < 30:
            mes = " おはようございます、"+self.user_name+"さん♪"
        if "おやすみ" in self.text and len(self.text) < 25:
            mes = " おやすみなさい、"+self.user_name+"さん♪"
        if "疲れた" in self.text and len(self.text) < 25:
            mes = "お疲れ様です、"+self.user_name+"さん♪"
        if "帰宅" in self.text and len(self.text) < 20:
            mes = " おかえりなさい、"+self.user_name+"さん♪"
        if "ただいま" in self.text and len(self.text) < 20:
            mes = " お疲れ様です♪お風呂にしますか？ご飯にしますか？それとも……\nうふふ♡"
        
        if mes != "":
            post_tweet_reply(self.from_id, self.tw_id, mes)
            return True
        else:
            return False
     
    
    # まゆ が呼ばれてれば反応して True を返す
    def hey_Mayu(self):
        
        mes = ""
        if "まゆ" in self.text:
            mes = "@"+self.from_id+" まゆですよぉ"
        if "こまゆり" in self.text:
            mes = "ああいうお顔がタイプなんですかぁ……？"
        if "まゆゆ" in self.text:
            mes = " ちがう人ですねぇ……？"
        if "まゆるど" in self.text:
            mes = "もう…ちゃんと\"まゆ\"って呼んでくださいっ"
        if "しいなまゆり" in self.text:
            mes = "トゥットゥルー♪"
            
        if mes != "":
            post_tweet_reply(self.from_id, self.tw_id, mes)
            return True
        else:
            return False
    
    
    def reply_specific_word(self):
        
        # if "再起動" in self.text:
        #     # エラーを起こす
        #     1/0
            
            
        try:
            
#             if "おめでとう" in self.text:
#                 post_tweet_reply(self.from_id, self.tw_id, "ありがとうございます♡\n"+self.user_name+"さんにお祝いしてもらえて、まゆ、うれしい…")
#                 return True
                
            
            # 登録が一番優先度高い
            if "円" in self.text:
                self.add_debt()
                return True
           
            # 全部済 の方が優先度高い、こっちが適用されるときは済みの方にいかない
            if "全部済" in self.text:
                self.debt_all_done()
                return True

            if "済" in self.text:
                self.debt_done()
                return True

            # 検索
            if "検索" in self.text:
                w = self.text.split("検索")[1]
                self.search_word(w)
                return True

            # 一覧を出す
            if "一覧" in self.text:
                msg = self.get_all_list()
                self.return_all_list(msg)
                return True

            # 差額を出す
            if "差額" in self.text:
                
                # 差額相手がリプライに含まれてない場合
                if len(self.member) == 0:
                    self.random_reply()
                else:
                    for mem in self.member:
                        self.return_diff_price(mem)
                
                return True
            
            if "イベント" in self.text:
                idx = self.text.find("イベント")
                w = self.text[idx+4:]
                self.search_events(w)
                return True
                
            # ヘルプ
            if ("ヘルプ" in self.text) or ("使い方" in self.text) or ("how to" in self.text) or ("help" in self.text) or ("Help" in self.text):
                mes = "参照してください♡\nhttps://twitter.com/otaku_shakkin/status/931263861742649344"
                post_tweet_reply(self.from_id, self.tw_id, mes)
                return True
            
            
            # あいさつ
            if self.greet():
                return True
            
            # リプライ時の「まゆ」には反応しない
            # まゆが含まれてたら「まゆですよぉ」
            # if self.hey_Mayu():
                # return True
            
            # どれにも一致しなかったら false 
            return False

        except:
            with open("../error.log", "r") as f:
                l = f.readlines()
                l = str(datetime.datetime.now()) + "\n==========\n\n" + str(traceback.format_exc()) +"\n==========\n\n\n\n" + "".join(l)
            with open("../error.log", "w") as f:
                print(l, file=f)
                
            return True
            
    
    # ランダムにリプライ
    def random_reply(self):
        with open("../data/Mayu_words.txt", "r") as f:
            lines = f.readlines()
            Mayu_words_db = list(map(lambda x:x.replace("\n", ""), lines))

        mes = random.choice(Mayu_words_db)
        post_tweet_reply(self.from_id, self.tw_id, mes)
        
      
    # マルコフ連鎖 + word2vec で会話
    def conversation(self):
        mayuchan = Mayu_conversation_bot(self.user_name)
        # 何パターン文章をつくるか
        m = 70
        mes = mayuchan.conversation(self.text, m)
        while len(mes) > 110:
            mes = mayuchan.conversation(self.text, m)
            
        post_tweet_reply(self.from_id, self.tw_id, mes)
        

    # TL に流れてる単語で反応するやつ
    def monitor_TL(self):
        if self.greet():
            return True
        if self.hey_Mayu():
            return True

            
    # 実行
    def run(self):    
        # リプライの場合
        if self.is_reply:
            
            # 特定ワードに反応させる
            if self.reply_specific_word():
                # print("specific")
                return True
            else:
                # print("random")
                # self.random_reply()
                self.conversation()
                return True
                
        else:
            if not self.is_conversation:
                # print("TL monitor")
                self.monitor_TL()
            
        return True
    
    
# ツイートの raw data の例
# ここの text を変えてインスタンス化すればいろいろ挙動を試せる
with open("../data/tweet_raw_data_example.json", "r") as f:
    tweeet_raw_data_example = json.load(f)
