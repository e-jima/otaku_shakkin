# -*- coding: utf-8 -*-

import tweepy
import datetime
import random
import pandas as pd
import numpy as np
import json
import re
from PIL import Image, ImageDraw, ImageFont
import traceback
import os
import shutil

path = "../shakkin_list/shakkin_list.csv"
bot_id = "otaku_shakkin"


def get_ymd(row):
    y = str(row.date).split(" ")[0].split("-")[0][2:]
    m = str(row.date).split(" ")[0].split("-")[1]
    d = str(row.date).split(" ")[0].split("-")[2]
    ymd = y+"/"+m+"/"+d
    return ymd

def back_up_df():
        now = str(datetime.datetime.now()).replace("-", "").replace(":", "").replace(" ", "").split(".")[0]
        bk_name = "shakkin_list_"+now+".csv"
        shutil.copy("../shakkin_list/shakkin_list.csv", "../shakkin_list/backup/"+bk_name)
        
# ららマジの曜日プレゼント
def rara_magi():
    # 曜日
    today = datetime.datetime.now().weekday()

    weekday = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]
    kigakubu = ["亜里砂・E・B,\n卯月真中華,\n奥村映,\n白石陽菜,\n洲崎麻衣,\n七瀬沙希,\n結城菜々美",
               "阿達悠花,\n綾瀬凜,\n楓智美,\n神田茜,\n島村珠樹,\n洲崎麻衣,\n園田乃愛,\n藤巻雪菜",
               "浅野葉月,\n阿達悠花,\n亜里砂・E・B,\n有栖川翼,\n卯月幸,\n神代結菜,\n神田茜,\n九条紗彩,\n白石陽菜,\n橘レイナ",
               "綾瀬凜,\n伊藤萌,\n奥村映,\n卯月真中華,\n楓智美,\n橘アンナ,\n七瀬沙希,\n南さくら",
               "浅野葉月,\n伊藤萌,\n瀬沢かなえ,\n橋本ひかり,\n藤巻雪菜,\n星崎梨花,\n向井春香",
                "小田桐アミ,\n神代結菜,\n瀬沢かなえ,\n橘アンナ,\n橘レイナ,\n月島塁,\n星崎梨花,\n三嶋蒼,\n南さくら,\n向井春香",
                "有栖川翼,\n卯月幸,\n小田桐アミ,\n九条紗彩,\n島村珠樹,\n園田乃愛,\n月島塁,\n橋本ひかり,\n三嶋蒼,\n結城菜々美"
               ]
    present = ["ブランド肉の贅沢ステーキ", "一昔前に流行した携帯型ゲーム", "おもちゃの指輪", "週刊お兄ちゃん",
                      "意識高い系ファッション誌", "月刊フー", "月刊フー"]

    mes = weekday[today]+": "+present[today]+"\n----------\n"+kigakubu[today]
    return mes

def omikuji():
    mes = ""

    daikichi = 0.01
    kichi = 0.03
    kyou = 1.0 - daikichi - kichi
    rnd = random.random()

    if rnd < daikichi:
        mes = "大吉です♡"
    elif rnd < kichi:
        mes = "吉です♪"
    else:
        mes = "凶です…"
    return mes

# ツイートするための画像を生成
def make_image(msg, use):
    base_image = Image.open("../images/base.png")
    draw = ImageDraw.Draw(base_image)
    f_size = 20
    b = (0, 0, 0)
    font = ImageFont.truetype("/Library/Fonts/ipaexg.ttf", f_size, encoding='utf-8')

    draw.text((10, 10), msg.decode("utf-8"), b, font=font)

    now = str(datetime.datetime.now()).replace("-", "").replace(":", "").replace(" ", "").split(".")[0]

    if use == "all_list":
        filepath = "../images/all_list/"+now+".png"
    if use == "diff_price":
        filepath = "../images/diff_price/"+now+".png"

    base_image.save(filepath)

    return filepath
        


class TwitterBot:
    
    def __init__(self, api, status):
        
        
        # api
        self.api = api
        
        # 一応保持しとく
        self.status = status
        
        # 借金リストの読み込み
        self.df = pd.read_csv(path, encoding="utf-8", parse_dates=[0])
        self.columns = self.df.columns
        # ツイート ID
        self.tw_id = status.id
        # 日時
        self.tw_date = status.created_at + datetime.timedelta(hours=9)
        # 誰からのリプライか
        self.from_id = status.author.screen_name
        # ユーザネーム
        self.user_name = status.author.name
        
        # bot へのリプライか？
        # デフォルトは False (=TL に流れてるだけ)
        self.is_reply = False
        
        # 誰へのリプライか？
        self.member = []
        for i in status._json["entities"]["user_mentions"]:
            user_id = i["screen_name"]
            #  @ に bot_id が含まれていたら is_reply を True に
            if user_id == bot_id:
                self.is_reply = True
            else:
                # bot 以外のメンション相手は member へ
                self.member.append(user_id)
           
        # @ID を全部抜いたテキストを抽出、空白も除去
        self.text = status.text.replace("@"+bot_id, "")
        for i in self.member:
            self.text = self.text.replace("@"+i, "")
        self.text = re.sub(r'\s', "", self.text)
        
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
    
    # ツイートさせる
    def tweet(mes):
        self.api.update_status(status=mes)
    
    
    # もらったメンションに対してリプライを送る
    def reply(mes, from_id, tw_id):
        mes = "@"+from_id+" "+mes
        self.api.update_status(status=mes, in_reply_to_status_id=tw_id)
    
    
    # 特定の相手にメンションする
    def mention(mes, to_id):
        mes = "@"+to_id+" "+mes
        self.api.update_status(status=mes)
    
    # あいさつ
    def greet_mes(self):
        mes = ""
        if "おは" in self.text and len(self.text) < 30:
            mes = "@"+self.from_id+" おはようございます、"+self.user_name+"さん♪"
        if "おやすみ" in self.text and len(self.text) < 25:
            mes = "@"+self.from_id+" おやすみなさい、"+self.user_name+"さん♪"
        if "帰宅" in self.text and len(self.text) < 20:
            mes = "@"+self.from_id+" おかえりなさい、"+self.user_name+"さん♪"
        if "ただいま" in self.text and len(self.text) < 20:
            mes = "@"+self.from_id+" お疲れ様です♪お風呂にしますか？ご飯にしますか？それとも……\nうふふ♡"
        
        if mes != "":
            self.api.update_status(status=mes, in_reply_to_status_id=self.tw_id)
            return True
        else:
            return False
     
    
    # まゆ が呼ばれてれば反応して True を返す
    def hey_Mayu(self):
        if "まゆゆ" in self.text:
            mes = "@"+self.from_id+" ちがう人ですねぇ…？"
            self.api.update_status(status=mes, in_reply_to_status_id=self.tw_id)
            return True

        if "まゆるど" in self.text:
            mes = "@"+self.from_id+ "もう…ちゃんと\"まゆ\"って呼んでくださいっ"
            self.api.update_status(status=mes, in_reply_to_status_id=self.tw_id)
            return True
            
        if "まゆ" in self.text:
            mes = "@"+self.from_id+" まゆですよぉ"
            self.api.update_status(status=mes, in_reply_to_status_id=self.tw_id)
            return True
        
        # この 3 種類でなければ False を返す
        return False
        
            
    # TL に反応するツイートがあるかどうか監視 
    def monitor_TL(self):
        # 優先度は あいさつ > まゆ
        if self.greet_mes():
            return True
        
        if self.hey_Mayu():
            return True
     
    
    def reply_Mayu(self):            
        # 優先度は あいさつ > まゆ > その他
        if self.greet_mes():
            return True
        if self.hey_Mayu():
            return True
        
        # どっちでもないとき
        self.Mayu_words()
        
        
        
    def Mayu_words(self):
        with open("../data/Mayu_words.txt", "r") as f:
            lines = f.readlines()
            Mayu_words_db = map(lambda x:x.replace("\n", ""), lines)
        
        mes = "@"+self.from_id+" "+random.choice(Mayu_words_db)
        self.api.update_status(status=mes, in_reply_to_status_id=self.tw_id)
        
        return True
        

    # エラーメッセージを返す
    def error_mes(self):
        mes = "@"+self.from_id+" エラーが発生しました…\n考えられる原因\n"
        mes = mes + "・文字数オーバー\n・検索対象ツイートが削除された\n・検索対象者にブロックされた など\n"
        mes = mes +"借金の更新に関するリプライをしてこのエラーが出た場合は、一覧、差額などを再度確認してください。"
        self.api.update_status(status=mes, in_reply_to_status_id=self.tw_id)
        return True
    
    
    # 借金登録
    def add_debt(self):
        for mem in self.member:
            lender_id = self.from_id
            borrower_id = mem
            if self.is_reverse:
                # 複数人への逆登録は弾く
                if len(self.member) == 1:
                    tmp = lender_id
                    lender_id = borrower_id
                    borrower_id = tmp
                else:
                    mes = "@"+self.from_id+" 意図した登録にならないかもしれません…\n逆登録の場合は一人に対してしかできません。"
                    self.api.update_status(status=mes, in_reply_to_status_id=self.tw_id)
                    return True

            # バックアップ
            back_up_df()

            price = self.text.split("円")[0]
            if price.isdigit():
                price = "{:,}".format(int(price))
            content = self.text.split("円")[-1]
            if content == "":
                content = "null"
            rh = self.get_random_hash()
            if self.is_reverse:
                mes = "登録完了です！(逆登録)\n"
            else:
                mes = "登録完了です！\n"
            mes = mes+"@"+lender_id+" から "+"@"+borrower_id+" へ\n"+price+"円: "+content+"\n#オタク借金\nID: "+rh
            self.api.update_status(status=mes, in_reply_to_status_id=self.tw_id)

            # 返信ツイートの ID を取得
            reply_id = self.api.user_timeline()[0].id
            # columns = [u'date', u'tweet_id', u'from_id', u'reply_id', u'id', u'price', u'content', u'lender', u'borrower', u'done']
            row = pd.DataFrame([[self.tw_date, str(self.tw_id), "@"+self.from_id, str(reply_id), rh, price, content, "@"+lender_id, "@"+borrower_id, 0]], columns=self.columns)
            self.df = self.df.append(row, ignore_index=True)
            
        self.df.to_csv(path, encoding="utf-8", index=False)
        return True
            
    
    # 借金済み
    def debt_done(self):
        
        # いきなり"済み"って送られてきたパターン
        if self.status.in_reply_to_status_id == None:
            self.Mayu_words()
            return False
         
        # リプライ元のツイート取得
        tw_in_rep = self.api.get_status(id=self.status.in_reply_to_status_id)
        
        # bot のツイートに対するリプライで、かつ bot の登録ツイートか?
        if (tw_in_rep.author.screen_name != bot_id) or ("ID: " not in tw_in_rep.text):
            self.Mayu_words()
            return False
        
        now = str(datetime.datetime.now()).replace("-", "").replace(":", "").replace(" ", "").split(".")[0]
        bk_name = "shakkin_list_"+now+".csv"
        shutil.copy("../shakkin_list/shakkin_list.csv", "../shakkin_list/backup/"+bk_name)

        done_id = tw_in_rep.text.split("ID: ")[-1]
        update_row = self.df[self.df.id == done_id]
        
        # その借金の貸し借りに関わっている人しか完了できない
        if list(update_row["borrower"] == "@"+self.from_id)[0] or list(update_row["lender"] == "@"+sef.from_id)[0]:
            self.df.loc[self.df.id == done_id, "done"] = 1
            self.df.to_csv(path, encoding="utf-8", index=False)
            # print 4
            mes = "@"+self.from_id+" "
            if update_row["borrower"].item() == "@"+self.from_id:
                mes = mes + update_row["lender"].item()+" 更新完了です！"
            else:
                mes = mes + update_row["borrower"].itme()+" 更新完了です！"
            self.api.update_status(status=mes, in_reply_to_status_id=self.tw_id)
            return True
        
        else:
            mes = "@"+self.from_id+" "+"あなたはこの借金に関わってませんねぇ…？"
            self.api.update_status(status=mes, in_reply_to_status_id=self.tw_id)
            return True
    
    
    # 借金全部済みのやつ   
    def debt_all_done(self):
        # いきなり"済み"って送られてきたパターン
        if self.status.in_reply_to_status_id == None:
            # self.Mayu_words()
            return False
        
        # リプライ元のツイート取得
        tw_in_rep = self.api.get_status(id=self.status.in_reply_to_status_id)
        
        # bot のツイートに対するリプライで、かつ bot の登録ツイートか?
        if (tw_in_rep.author.screen_name != bot_id) or ("ID: " not in tw_in_rep.text):
            # self.Mayu_words()
            return False
        
        done_ids = tw_in_rep.text.split("ID: ")[-1].split(" ")[0].split("/")[:-1]
        if len(done_ids) == 0:
            mes = "@"+self.from_id+" 更新できるものはありませんでした…"
            self.api.update_status(status=mes, in_reply_to_status_id=self.tw_id)
            return True
        
        # バックアップ
        back_up_df()
        
        for done_id in done_ids:

            update_row = self.df[self.df.id==done_id]
            
            # お相手さん
            if update_row["borrower"].item() == "@"+self.from_id:
                man = update_row["lender"].item()
            else:
                man = update_row["borrower"].item()
                
            reply_id = list(update_row.reply_id)[0]

            # 借金に関わってる人かどうかは保証されてる
            self.df.loc[self.df.id == done_id, "done"] = 1
            try:
                self.api.update_status(status="これは更新されました♡\n"+str(datetime.datetime.now()), in_reply_to_status_id=reply_id)
            except:
                self.error_mes()
                return True

        self.df.to_csv(path, encoding="utf-8", index=False)
        mes = "@"+self.from_id+" "+man+" 全て更新完了しました♡"
        self.api.update_status(status=mes, in_reply_to_status_id=self.tw_id)
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

        search_df = df[map(lambda x: (x[0] | x[1]) & x[2] & (w in x[3]), 
                           zip(list(df.lender==from_id), list(df.borrower==from_id), list(df.done==0.0), list(df.content)))]

        mes = ""
        for i in range(len(search_df)):
            tmp = search_df.iloc[i]
            mes = mes + "https://twitter.com/"+tmp.from_id.replace("@", "")+"/status/"+str(tmp.tweet_id)+"\n"
            
        return mes

        
    # リプライの特定ワードに反応するやつ
    # 引数: 反応させたい特定ワードとtext
    def word_reaction_reply(self):
        
        
        # エラーを起こさせて再起動
        if "再起動" in self.text:
            with open("../error.log", "r") as f:
                l = f.readlines()
                l = str(datetime.datetime.now()) + "\n==========\n\n" + str("再起動") +"\n==========\n\n\n\n" + "".join(l)
            with open("../error.log", "w") as f:
                print >> f, l
                
            mes = "@" + self.from_id+" 再起動しました♡"
            self.api.update_status(status=mes, in_reply_to_status_id=self.tw_id)
                
            # 強制エラー
            1/0
            return 0 # できないけど

        try:

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
                search_list = self.search_word(w)
                mes = "@"+self.from_id+" これですかぁ？\n"+search_list
                if search_list == "":
                    mes = "@"+self.from_id+" 指定の検索ワードでの登録は見つかりませんでした…"

                self.api.update_status(status=mes, in_reply_to_status_id=self.tw_id)


                return True

            # 一覧を出す
            if "一覧" in self.text:
                msg = self.get_all_list()
                filepath = make_image(msg, "all_list")
                mes = "@"+self.from_id+" どうぞ♡"
                self.api.update_with_media(status=mes, in_reply_to_status_id=self.tw_id, filename=filepath)
                return True

            # 差額を出す
            if "差額" in self.text:
                
                if len(self.member) == 0:
                    Mayu_words()
                    return True

                for mem in self.member:
                    # all_id は、差額対象ツイ全部のID
                    msg, all_id = self.calc_diff_price(mem)
                    if all_id == "":
                        all_id = "なし"
                    filepath = make_image(msg, "diff_price")
                    # print filepath
                    mes = "@"+self.from_id+" .@"+mem+" さんとの差額です♡\nID: "+all_id
                    self.api.update_with_media(status=mes, in_reply_to_status_id=self.tw_id, filename=filepath)

                return True

            # おみくじ10連
            if  "10連" in self.text:
                mes = "@"+self.from_id+" "
                for i in range(10):
                    mes = mes+omikuji()+"\n"

                if "大吉" in mes:
                    mayu_pictures =  os.listdir("../data/Mayu_pic/")
                    filepath = random.choice(mayu_pictures)
                    self.api.update_with_media(status=mes, in_reply_to_status_id=self.tw_id, filename=filepath)
                else:
                    self.api.update_status(status=mes, in_reply_to_status_id=self.tw_id)

                return True

            # おみくじ 
            if "おみくじ" in self.text:
                mes = "@"+self.from_id+" "+omikuji()
                self.api.update_status(status=mes, in_reply_to_status_id=self.tw_id)
                return True

            if "大吉" in self.text:
                mes = "@"+self.from_id+" 大吉です♪"
                mayu_pictures =  os.listdir("../data/Mayu_pic/")
                filepath = random.choice(mayu_pictures)
                self.api.update_with_media(status=mes, in_reply_to_status_id=self.tw_id, filename=filepath)
                return True

            # ららマジ
            if "ららマジ" in self.text:
                mes = "@"+self.from_id+" "+rara_magi()
                self.api.update_status(status=mes, in_reply_to_status_id=self.tw_id)
                return True

            # ヘルプ
            if ("ヘルプ" in self.text) or ("使い方" in self.text) or ("how to" in self.text) or ("help" in self.text):
                mes = "@"+self.from_id+" 参照してください♡\nhttps://twitter.com/otaku_shakkin/status/931263861742649344"
                self.api.update_status(status=mes, in_reply_to_status_id=self.tw_id)
                return True

            # どれにも一致しなかったら false 
            return False

        except:
                
            with open("../error.log", "r") as f:
                l = f.readlines()
                l = str(datetime.datetime.now()) + "\n==========\n\n" + str(traceback.format_exc()) +"\n==========\n\n\n\n" + "".join(l)
            with open("../error.log", "w") as f:
                print >> f, l
                
            self.error_mes()
            return True