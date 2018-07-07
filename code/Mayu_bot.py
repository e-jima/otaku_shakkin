import MeCab
import pandas as pd
import random
import collections
import os
import numpy as np
from gensim.models import word2vec

# 終端文字
endword = ["。", "♪", "!", "?", "？", "！", "♡", ")", "）"]

# word2vec モデルの読み込み
model = word2vec.Word2Vec.load("../data/word2vec/wiki.model")

# 分かち書き
def wakati(text):
    t = MeCab.Tagger("-Owakati")
    m = t.parse(text)
    result = m.rstrip(" \n").split(" ")
    
    return result

# まゆの発言を読み込む
def load_mayu_text():
    mayu_text = []
    # カードのテキスト
    mayu = pd.read_table("../data/Mayu_text/Mayu.txt", sep="\t", header=None)
    mayu.columns = ["card", "text"]
    # 全角スペースを消す
    text = list(map(lambda x: x.replace('\u3000', ""), list(mayu.text)))
    # テキストの終わりに終端文字がない場合に付け加える
    mayu_text += list(map(lambda x: x if x[-1] in endword else x+random.choice(["…", "♡", "♪"]), text))

    # limited commu
    mayu_limited = pd.read_table("../data/Mayu_text/Mayu_limited.txt", sep="t", header=None)
    mayu_limited.columns = ["text"]
    text = list(map(lambda x: x.replace('\u3000', "").replace("\xa0", ""), list(mayu_limited.text)))
    mayu_text += list(map(lambda x: x if x[-1] in endword else x+"…", text))

    # デレステのコミュ
    mayu_dellesta = pd.read_table("../data/Mayu_text/Mayu_dellesta_commu.txt", sep="\t", header=None)
    mayu_dellesta.columns = ["speaker", "text"]
    mayu_text += list(mayu_dellesta[mayu_dellesta.speaker == "まゆ"].text)

    # デレステのエヴリデイドリームコミュ
    dellesta_everydaydream = pd.read_table("../data/Mayu_text/Mayu_everydaydream_commu.txt", sep="\t", header=None)
    dellesta_everydaydream.columns = ["speaker", "text"]
    mayu_text += list(dellesta_everydaydream[dellesta_everydaydream.speaker == "まゆ"].text)
    
    # エヴリデイドリームの歌詞
    with open("../data/Mayu_text/everydaydream.txt", "r") as f:
        lines = f.readlines()
    for l in lines:
        mayu_text += l[:-1]
        
    # マイスイートハネムーンの歌詞
    with open("../data/Mayu_text/my_sweet_honeymoon.txt", "r") as f:
        lines = f.readlines()
    for l in lines:
        mayu_text += l[:-1]
    
    # # SS 
    mayu_SS = pd.DataFrame()
    for fn in os.listdir("../data/Mayu_text/SS"):
        if ".txt" in fn:
            tmp = pd.read_table("../data/Mayu_text/SS/"+fn, sep="\t", header=None)
            mayu_SS = mayu_SS.append(tmp)

    mayu_SS.columns = ["speaker", "text"]
    text = list(mayu_SS[mayu_SS.speaker == "まゆ"].text)
    text = list(map(lambda x: x.replace('\u3000', ""), text))
    mayu_text += list(map(lambda x: x if x[-1] in endword else x+random.choice(["…", "♡", "♪"]), text))
    
    return mayu_text


def get_wordlist_and_init_word(mayu_text):
    wordlist = []
    # 先頭に来たことがある言葉
    initial_word = []
    for t in mayu_text:
        wkt = wakati(t)
        wordlist += wkt
        initial_word.append(wkt[0])
    
    # 最初にくるワード top 100
    initial_word = sorted(dict(collections.Counter(initial_word)).items(), 
                          key=lambda x: x[1], reverse=True)
    initial_word = list(map(lambda x: x[0], initial_word[:100]))
    
    
    return wordlist, initial_word




# 毎回計算するのは遅いので、起動のとき一回だけ計算
# mayu_text を新しくした場合は、システム全体を再起動
mayu_text = load_mayu_text()
wordlist, initial_word = get_wordlist_and_init_word(mayu_text)





# 文章を単語と品詞に分解
def text_parse2node(text):
    mt = MeCab.Tagger('')
    mt.parse('')
    node = mt.parseToNode(text)
    
    # 名詞、動詞、形容詞
    noun = []
    verb = []
    adjective = []

    k = 0
    while node != None:
        fields = node.feature.split(",")
        if fields[0] == "名詞":
            noun.append(node.surface)
        if fields[0] == "動詞":
            verb.append(node.surface)
        if fields[0] == "形容詞":
            adjective.append(node.surface)

        node = node.next
        
    return noun, verb, adjective
    
# 文章の中の名詞、動詞、形容詞に限定してベクトルを作成し、ベクトルの平均値を取る
def get_vector(text):
    mt = MeCab.Tagger('')
    mt.parse('')

    sum_vec = np.zeros(200)
    word_count = 0
    node = mt.parseToNode(text)
    while node != None:
        fields = node.feature.split(",")
        # 名詞、動詞、形容詞に限定
        if fields[0] == '名詞' or fields[0] == '動詞' or fields[0] == '形容詞':
            try:
                sum_vec += model.wv[node.surface]
                word_count +=1
            except:
                pass
        node = node.next
    
    return sum_vec / word_count


# cos類似度
def cos_sim(v1, v2):
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))


# 文章作成
def create_text(break_count):
    # マルコフ連鎖の辞書
    markov = {}
    for w1, w2, w3, w4 in zip(wordlist, wordlist[1:], wordlist[2:], wordlist[3:]):
        if (w1, w2, w3) not in markov:
            markov[(w1, w2, w3)] = []
        markov[(w1, w2, w3)].append(w4)
           
    count = 0
    w1, w2, w3 = random.choice(list(markov.keys()))    
    # 最初の一語は、今までも文頭に来たことがあるやつだけにする
    # 助詞を除くため、length が 1 は除外
    while w1 not in initial_word or len(w1) < 2:
        w1, w2, w3= random.choice(list(markov.keys()))
        
    sentence = w1+w2+w3
    while count < len(wordlist):
        tmp = random.choice(markov[(w1, w2, w3)])
        sentence += tmp
        
        # 終端文字が来たら
        if tmp in endword:
            tmp += "/"
            count += 1

        w1, w2, w3 = w2, w3, tmp
        if count == break_count:
            break

    return sentence


def translate_special_word(text):
    if "しゅき" in text:
        text.replace("しゅき", "好き")
       
    return text


class Mayu_conversation_bot():
    
    def __init__(self, producername):
        self.producername = producername
        
    
    def conversation(self, input_text, m):

        # 特殊文字列の変換
        input_text = translate_special_word(input_text)
       

        # 入力テキストをベクトル化
        v_input = get_vector(input_text)
        # 計算できなかった場合は、まゆの発言からランダムに
        while np.any(np.isnan(v_input)):
            v_input = get_vector(random.choice(mayu_text))

        # m 個文章を作る
        sentences = []
        for i in range(m):
            # 引数はセンテンスを何個つなげるか
            text = create_text(1)
            sentences.append(text.replace("producername", self.producername))

        # 一番 cos類似度が高い文章を返す
        cs_max = -1
        res = ""
        for s in sentences:
            v = get_vector(s)
            cs = cos_sim(v, v_input)
        #     print(s, end="")
        #     print(cs)
            if cs > cs_max:
                cs_max = cs
                res = s

        return res