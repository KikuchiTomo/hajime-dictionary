"""辞書に足す語のうち，変換の候補や文節の区切りを乱す壊れた書き方を見分ける(tools/merge_mozc.py・tools/add_ut.py・tools/add_neologd.py・
tools/add_sudachi.py で共通)．

除く語(broken が理由を返す)
- 読みが促音で始まる(「ッチュネン」→ っちゅねん!，「ッオキナ」)．語は促音から始まらない．語の途中で切った切れ端
- 数詞の促音の読み(「ジュウイッ」→ 十一，「サンジュッ」→ 三拾)．数と助数詞をつなぐ形(八本 の「ハッ」→ 八)は azooKey の辞書の
  数詞にあり，足す語は文節の切れ端にしかならない
- 促音で切った交ぜ書き(「ハッセイ」→ はっ声・ハッ声，「アッセイ」→ アッ制，「ケッタイ」→ けっ滞)．同じ読みに漢字だけの名詞があり，
  その語の常用漢字を，促音で終わる読みのかなに置き換えた書き方．漢語の頭の字(発・圧・決)を読みのかなにした形で，新聞や公用文の交ぜ書き
  (改ざん・破たん．常用漢字でない字や，かつて常用漢字でなかった字をかなにする)とは違い，習わしとして使われない．
  送りがなの促音(引っ越し・ぶっ飛ぶ・取っ手)は，元の語の漢字の位置に当たらないので当たらない
- 読みのかなだけの名詞(「ハッセイ」→ はっせい・ハッセイ，「リクグン」→ リクグン)．同じ読みに，その語より KANA_MARGIN 以上よく使う
  (値の大きい)漢字を含む名詞があるときに限る．ひらがなとカタカナの候補は変換エンジンが作るので，辞書の語は要らない．
  カタカナで書くのが習わしの語(ギンザケ・イワツバメ)は漢字の語と同じくらいよく使われるので残る．人名は見ない

azooKey の辞書の語は，次の文節の切れ端だけを除く(azookey_fragment)．どれも前後の語とつながり，「はッ制」「イッ所に」「はっ再の」
のような候補を作るため．数と助数詞をつなぐ数詞(ハッ → 八・8)，接尾の語(っ子・っぽい・っぱなし)，感動詞と副詞(ハッとする の「ハッ」)は残す
- 読みが促音で始まる，カタカナだけの名詞(ッ・ック・ット)
- 読みが促音で終わる 2 文字の，カタカナだけの名詞(イッ・セッ・ガッ)
- 読みが促音で終わる，かなで書いた数詞(はっ・いっ・じっ)
- 促音で切った交ぜ書きの名詞(てっ底・やっ介・まっ赤・ひっ算)．同じ読みの漢字だけの名詞(徹底・厄介)が azooKey の辞書にあるもの．
  新聞の交ぜ書きとして定着した語(うっ血・ぼっ発・かっ色・しっ責 など．NEWSPAPER_MIXED_SPELLINGS)は残す
- 送りがなを落とした 1 字の一般名詞(待 まち・書 かき・考 かんがえ・驚 おどろき)．同じ字の動詞の連用形と読みが同じで，送りがなを付けた
  名詞(待ち・書き)のほうが OKURIGANA_MARGIN 以上よく使われるもの(dropped_okurigana)．SudachiDict から足す語にも当てる(足し直さないため)．Zenzai が 1 語の「まち」を「待」にする．
  「送り仮名の付け方」(1973)の通則 2 の例外で送りがなを付けない名詞(光・隣・氷・恋・組・帯・畳．NO_OKURIGANA_NOUNS)と，
  複合語の頭以外に付く読み(濁る読み「ズミ」「ガキ」)と，接尾・助数詞の品詞の語(確認済・但し書 に使う)は残す
"""
import collections
import re
import zipfile

KATAKANA_TO_HIRAGANA = {code: code - 0x60 for code in range(0x30A1, 0x30F7)}
SOKUON = "ッ"
# 数を表す字．数詞の促音の読みの語がこれだけでできていれば除く
NUMERALS = set("0123456789０１２３４５６７８９〇零一二三四五六七八九十百千万億兆壱弐参肆伍陸漆捌玖拾廿卅")
NUMERALS |= {chr(code) for code in range(0x2160, 0x2189)}
# 読みのかなだけの語を除くのに要る，漢字を含む語との値(対数の確率に近い)の差．カタカナで書くのが習わしの生き物の名前は
# 漢字の語との差が 2 ほどまで(ギンザケ と 銀鮭)，読みをカタカナにしただけの語は 5 以上(ハッセイ と 発生)
KANA_MARGIN = 3.0
KANJI_CLASS = "[㐀-鿿豈-﫿\U00020000-\U0002fa1f々〆]"


def is_kanji(character):
    code = ord(character)
    return (0x4E00 <= code <= 0x9FFF or 0x3400 <= code <= 0x4DBF or 0xF900 <= code <= 0xFAFF or 0x20000 <= code <= 0x2FA1F
            or character in "々〆")


def is_kana(character):
    code = ord(character)
    # ヵヶは「か」「が」「こ」と読む漢字の略なので，かなとして見ない(数十ヵ所)
    return (0x3041 <= code <= 0x3096 or 0x30A1 <= code <= 0x30FA or character == "ー") and character not in "ヵヶ"


def load_joyo(unihan_zip):
    """常用漢字表(2010)の漢字．Unicode の Unihan データベース(Unihan_OtherMappings.txt の kJoyoKanji)から読む．
    許容字体(剥・叱・填・頬)は kJoyoKanji の値が常用漢字の符号位置になっている行なので，その字も含める"""
    joyo = set()
    with zipfile.ZipFile(unihan_zip) as archive:
        for line in archive.read("Unihan_OtherMappings.txt").decode("utf-8").splitlines():
            columns = line.split("\t")
            if len(columns) == 3 and columns[1] == "kJoyoKanji":
                joyo.add(chr(int(columns[0][2:], 16)))
    if len(joyo) < 2136:
        raise ValueError(f"常用漢字が足りません({len(joyo)} 字)")
    return frozenset(joyo)


class SameReadingWords:
    """読みごとの既存の名詞．交ぜ書きと読みのかなだけの語を見分けるのに使う．同じ読みの動詞や形容詞(「アオザメ」に対する
    「青ざめ」)とは比べない"""

    def __init__(self):
        self.kanji_only = {}
        self.best_with_kanji = {}

    def add(self, reading, word, value, feature):
        """feature は IPAdic の品詞．名詞だけを覚える"""
        if feature.startswith("名詞") and any(is_kanji(c) for c in word):
            self.best_with_kanji[reading] = max(value, self.best_with_kanji.get(reading, value))
            if all(is_kanji(c) for c in word):
                self.kanji_only.setdefault(reading, set()).add(word)


def split_by_sokuon(reading, word, same_reading, joyo):
    """漢字だけの語の常用漢字を，促音で終わる読みのかなに置き換えた書き方か(はっ声 と 発声)"""
    runs = []
    for character in word:
        kind = "kana" if is_kana(character) else "kanji" if is_kanji(character) else None
        if kind is None:
            return False
        if runs and runs[-1][0] == kind:
            runs[-1][1] += character
        else:
            runs.append([kind, character])
    # 促音で終わるかなのすぐあとに漢字が続くところが要る
    if not any(kind == "kana" and text[-1] in "っッ" and index + 1 < len(runs) for index, (kind, text) in enumerate(runs)):
        return False
    pattern = re.compile("".join(f"({KANJI_CLASS}+)" if kind == "kana" else re.escape(text) for kind, text in runs))
    for original in same_reading.kanji_only.get(reading, ()):
        match = pattern.fullmatch(original)
        if match and all(c in joyo for c in "".join(match.groups())):
            return True
    return False


def azookey_fragment(reading, word, feature):
    """azooKey の辞書の語のうち，除く文節の切れ端か．feature は IPAdic の品詞"""
    if not feature.startswith("名詞"):
        return None
    katakana = all(0x30A1 <= ord(c) <= 0x30FA or c == "ー" for c in word)
    if reading.startswith(SOKUON) and katakana and not feature.startswith("名詞,接尾,一般"):
        return "読みが促音で始まるカタカナの名詞"
    if len(reading) == 2 and reading.endswith(SOKUON) and katakana:
        return "促音で終わる 2 文字のカタカナの名詞"
    if feature.startswith("名詞,数") and reading.endswith(SOKUON) and all(is_kana(c) for c in word):
        return "かなで書いた数詞の促音の読み"
    return None


# azooKey の辞書の促音で切った交ぜ書きの名詞のうち，残すもの．常用漢字になる前の表外字(鬱・勃・褐・叱・闊・抹)をかなにした，
# 新聞や公用文で使われてきた書き方
NEWSPAPER_MIXED_SPELLINGS = {"うっ屈", "うっ血", "うっ積", "うっ憤", "うっ滞", "かっ歩", "かっ色", "しっ責", "ぼっ発", "まっ消"}


# 「送り仮名の付け方」(1973)の通則 2 の例外: 活用のある語から転じた名詞で，送りがなを付けない語
NO_OKURIGANA_NOUNS = set("謡虞趣氷印頂帯畳卸煙恋志次隣富恥話光舞折係掛組肥並巻割")
# 送りがなを落とした名詞を見分けるのに要る，送りがなを付けた名詞との値(対数の確率に近い)の差
OKURIGANA_MARGIN = 2.0
# 動詞の連用形の読みの終わり(イ段・エ段)
CONTINUATIVE_ENDINGS = set("イキシチニヒミリギジヂビピィエケセテネヘメレゲゼデベペェ")
# 複合語の頭以外でだけ使う，濁った頭の読み(確認ズミ・但しガキ)
VOICED_INITIALS = set("ガギグゲゴザジズゼゾダヂヅデドバビブベボパピプペポ")


class OkuriganaNouns:
    """読みごとの名詞の値と，漢字に送りがなを付けた動詞の書き方．送りがなを落とした 1 字の名詞を見分けるのに使う"""

    def __init__(self):
        self.noun_values = {}
        self.verb_spellings = collections.defaultdict(set)

    def add(self, reading, word, value, feature):
        """feature は IPAdic の品詞"""
        if feature.startswith("名詞"):
            key = (reading, word)
            self.noun_values[key] = max(value, self.noun_values.get(key, value))
        elif feature.startswith("動詞") and len(word) > 1 and is_kanji(word[0]) and all(0x3041 <= ord(c) <= 0x3096 for c in word[1:]):
            self.verb_spellings[reading].add(word)


def dropped_okurigana(reading, word, value, feature, okurigana):
    """除く送りがなを落とした 1 字の一般名詞か．value はその語の値，okurigana は既存の語(OkuriganaNouns)"""
    if (not feature.startswith("名詞,一般") or len(word) != 1 or not is_kanji(word) or word in NO_OKURIGANA_NOUNS
            or reading[-1] not in CONTINUATIVE_ENDINGS or reading[0] in VOICED_INITIALS):
        return None
    for spelling in okurigana.verb_spellings.get(reading, ()):
        if spelling[0] == word and okurigana.noun_values.get((reading, spelling), float("-inf")) >= value + OKURIGANA_MARGIN:
            return "送りがなを落とした 1 字の名詞"
    return None


def azookey_mixed_spelling(reading, word, feature, azookey_words, joyo):
    """azooKey の辞書の語のうち，除く促音で切った交ぜ書きの名詞か．azookey_words は azooKey の辞書の語(SameReadingWords)"""
    if not feature.startswith("名詞") or feature.startswith("名詞,固有名詞,人名") or word in NEWSPAPER_MIXED_SPELLINGS:
        return None
    return "促音で切った交ぜ書きの名詞" if split_by_sokuon(reading, word, azookey_words, joyo) else None


def broken(reading, word, value, same_reading, joyo, noun=True, name=False):
    """除く理由．除かないなら None．reading はカタカナ，value は足すときの値，same_reading は既存の語(SameReadingWords)．
    noun は名詞か，name は人名か(品詞で決める)"""
    if reading.startswith(SOKUON):
        return "読みが促音で始まる"
    if reading.endswith(SOKUON) and all(c in NUMERALS for c in word):
        return "数詞の促音の読み"
    if name:
        return None
    if split_by_sokuon(reading, word, same_reading, joyo):
        return "促音で切った交ぜ書き"
    if (noun and word in (reading, reading.translate(KATAKANA_TO_HIRAGANA))
            and same_reading.best_with_kanji.get(reading, float("-inf")) >= value + KANA_MARGIN):
        return "読みのかなだけ"
    return None
