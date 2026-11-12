"""辞書に語を足すときに除く語の決まり(tools/add_ut.py・tools/add_neologd.py・tools/add_sudachi.py で共通)．

除く語
- 読みが MIN_READING_LENGTH 文字より短いか，MAX_READING_LENGTH 文字より長い．短い読みは既存の語と同じ読みになりやすく，
  長い読み(住所の全体，作品の題名)は普段の変換で打つことがまれなため
- 表記が MAX_WORD_LENGTH 文字より長いか，ALLOWED_SYMBOLS 以外の記号・ほかの文字体系(ハングル・ギリシャ文字など)を含む
- 表記が記号と数字だけ
- 表記のかなが読みと合わない．表記のかなの部分は，その順に読みに現れなければならない(漢字・英字・数字の部分は 1 文字以上の読み．
  漢字に挟まれたケは漢字と同じに扱う)
- 表記が英字だけ(と ALLOWED_SYMBOLS)で，英字を 1 文字ずつ読んだ読みでも，子音の並びが似た読み(tools/spelling.py)でもない
"""
import pathlib
import re
import sys

# 同じディレクトリの spelling.py を読む(python3 -I ではスクリプトの場所が探す場所に入らないため)
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from spelling import similar, spelled_out  # noqa: E402

MIN_READING_LENGTH = 4
MAX_READING_LENGTH = 20
MAX_WORD_LENGTH = 20
# 英字の語を tools/spelling.py で比べるときの共通の部分の割合の下限(tools/fetch_wikidata.py と同じ)
SPELLING_THRESHOLD = 0.8
# 表記に入れてよい記号．名前によく使うものだけ
ALLOWED_SYMBOLS = set(" ・=-&'.!?")

# ひらがな(ぁ〜ゖ)をカタカナにする．azooKey の読みはカタカナ
HIRAGANA_TO_KATAKANA = {code: code + 0x60 for code in range(0x3041, 0x3097)}
# 表記のかなを読みと比べるときの置き換え．ゐゑは UT 辞書の読みでいえになっている
KANA_IN_WORD = {**HIRAGANA_TO_KATAKANA, ord("ヰ"): "イ", ord("ヱ"): "エ", ord("ゐ"): "イ", ord("ゑ"): "エ"}
READING = re.compile("[ァ-ヴー]+")


def char_class(c):
    """表記の 1 文字の種類．kana は読みと比べる文字，other は 1 文字以上の読みになる文字，symbol は読みにならない文字，None は使えない文字"""
    code = ord(c)
    if 0x3041 <= code <= 0x3096 or 0x30A1 <= code <= 0x30FA or c == "ー":
        # ヵヶは「か」「が」「こ」と読むことがあるので，かなとして比べない
        return "other" if c in "ヵヶ" else "kana"
    if (0x4E00 <= code <= 0x9FFF or 0x3400 <= code <= 0x4DBF or 0xF900 <= code <= 0xFAFF or 0x20000 <= code <= 0x2FA1F
            or c in "々〆〇ゝゞヽヾ"):
        return "other"
    if c.isascii() and c.isalnum():
        return "other"
    if c in ALLOWED_SYMBOLS:
        return "symbol"
    return None


def problem(reading, word):
    """除く理由．除かないなら None"""
    if not READING.fullmatch(reading):
        return "読みがかな以外"
    if len(reading) < MIN_READING_LENGTH:
        return "読みが短い"
    if len(reading) > MAX_READING_LENGTH:
        return "読みが長い"
    if len(word) > MAX_WORD_LENGTH:
        return "表記が長い"
    classes = [char_class(c) for c in word]
    if None in classes:
        return "表記に使えない文字"
    if not any(c.isalpha() for c in word):
        return "表記が記号と数字だけ"
    if all(c.isascii() or kind == "symbol" for c, kind in zip(word, classes)):
        letters = "".join(c for c in word if c.isascii() and c.isalnum())
        if letters.isalpha() and (spelled_out(reading, letters) or similar(reading, letters, SPELLING_THRESHOLD)):
            return None
        return "英字の表記が読みと合わない"
    # 表記のかなの部分が，その順に読みに現れるか．かな以外の文字の並びは 1 文字以上の読みにする．
    # 漢字に挟まれたケは「が」「か」と読むことが多いので(松ケ崎)，漢字と同じに扱う．& は読みに「アンド」などが入ってよい
    pattern = []
    for index, (c, kind) in enumerate(zip(word, classes)):
        if c == "ケ" and 0 < index < len(word) - 1 and classes[index - 1] == classes[index + 1] == "other":
            kind = "other"
        if kind == "kana":
            pattern.append(re.escape(c.translate(KANA_IN_WORD)))
        elif kind == "other" and (not pattern or pattern[-1] != ".+"):
            pattern.append(".+")
        elif c == "&":
            pattern.append(".*")
    if not re.fullmatch("".join(pattern), reading):
        return "表記のかなが読みと合わない"
    return None
