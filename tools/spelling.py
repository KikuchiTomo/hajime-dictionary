"""カタカナの読みと英字の綴りが同じ音を表すかを，子音の並びで見積もる．tools/fetch_wikidata.py と tools/add_ut.py が使う．

- similar: 子音の並びが似ていて(共通の部分の割合が threshold 以上)，最初と最後の子音が同じなら真
- spelled_out: 英字の略語(IHI，NHK)を 1 文字ずつ読んだ読みと一致すれば真
"""
import re

# カタカナをローマ字にする表．子音の並びを比べるためだけに使うので，長音と促音は捨てる
KANA = dict(zip(
    "アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヰヱヲン"
    "ガギグゲゴザジズゼゾダヂヅデドバビブベボパピプペポヴァィゥェォャュョヮ",
    "a i u e o ka ki ku ke ko sa shi su se so ta chi tsu te to na ni nu ne no ha hi fu he ho ma mi mu me mo ya yu yo "
    "ra ri ru re ro wa i e o n ga gi gu ge go za ji zu ze zo da ji zu de do ba bi bu be bo pa pi pu pe po vu "
    "a i u e o ya yu yo wa".split(),
))
assert len(KANA) == 83
CONSONANTS = {"k": "K", "g": "K", "q": "K", "c": "K", "x": "K", "s": "S", "z": "S", "j": "S", "t": "T", "d": "T",
              "n": "N", "m": "N", "h": "H", "f": "H", "b": "P", "p": "P", "v": "P", "r": "R", "l": "R", "C": "C"}
# 英字 1 文字の読み．よく使う揺れも入れる
LETTER_NAMES = {
    "A": ["エー", "エイ"], "B": ["ビー"], "C": ["シー"], "D": ["ディー", "デー"], "E": ["イー"], "F": ["エフ"],
    "G": ["ジー"], "H": ["エイチ", "エッチ"], "I": ["アイ"], "J": ["ジェー", "ジェイ"], "K": ["ケー", "ケイ"],
    "L": ["エル"], "M": ["エム"], "N": ["エヌ"], "O": ["オー"], "P": ["ピー"], "Q": ["キュー"], "R": ["アール"],
    "S": ["エス"], "T": ["ティー", "テー"], "U": ["ユー"], "V": ["ブイ", "ヴィー"], "W": ["ダブリュー", "ダブリュ", "ダブル"],
    "X": ["エックス"], "Y": ["ワイ"], "Z": ["ゼット", "ズィー"],
}


def skeleton(text, english):
    """子音の並び．似た音の子音は同じ文字にまとめ，母音と半母音(w・y)は捨てる"""
    letters = re.sub("[^a-z]", "", text.lower())
    if english:
        letters = re.sub("c(?=[eiy])", "s", letters)
        for before, after in [("ph", "f"), ("th", "s"), ("ck", "k"), ("qu", "kw"), ("gh", ""), ("wh", "w"), ("x", "ks")]:
            letters = letters.replace(before, after)
        # 母音の前にない r はカタカナでは長音になる(network → ネットワーク)
        letters = re.sub("r(?![aeiouy])", "", letters)
    for before, after in [("sh", "s"), ("ch", "C"), ("ts", "t"), ("tz", "t")]:
        letters = letters.replace(before, after)
    result = []
    for letter in letters:
        value = CONSONANTS.get(letter)
        if value and (not result or result[-1] != value):
            result.append(value)
    return "".join(result)


def common_length(a, b):
    previous = [0] * (len(b) + 1)
    for x in a:
        current = [0]
        for j, y in enumerate(b):
            current.append(previous[j] + 1 if x == y else max(previous[j + 1], current[j]))
        previous = current
    return previous[-1]


def similar(katakana, english, threshold):
    a = skeleton("".join(KANA.get(c, "") for c in katakana), False)
    b = skeleton(english, True)
    if min(len(a), len(b)) < 2 or a[0] != b[0] or a[-1] != b[-1]:
        return False
    return 2 * common_length(a, b) / (len(a) + len(b)) >= threshold


def spelled_out(katakana, letters):
    """大文字の英字だけの綴りを，1 文字ずつ読んだものが読みと一致するか"""
    if not letters or not all("A" <= c <= "Z" for c in letters):
        return False
    pattern = "".join("(?:" + "|".join(LETTER_NAMES[c]) + ")" for c in letters)
    return re.fullmatch(pattern, katakana) is not None
