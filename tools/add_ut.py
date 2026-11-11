"""worddict に，Mozc UT 辞書(utuhiro78 さんの mozcdic-ut-*)の語を足す．

使い方:
    python3 -I tools/add_ut.py <worddict.tsv> <UT 辞書の置き場所> <IPAdic の left-id.def> <出力.tsv>

UT 辞書の置き場所には mozcdic-ut-<名前>.txt.bz2 を置く(tools/fetch_sources.sh が取得する)．1 行は Mozc の辞書と同じ
「読み(ひらがな)<TAB>左 ID<TAB>右 ID<TAB>コスト<TAB>表記」だが，ID はすべて 0000 で品詞は無い．

- 足すのは「読み・表記」の組が worddict に無いものだけ．既存の語の値は変えない
- 品詞(IPAdic の left-id)は辞書ごとに決める(SOURCES)．人名と地名の辞書はそれぞれの固有名詞，SudachiDict と NEologd は
  品詞が分からないので「名詞,固有名詞,一般」(Hajime IME がユーザー辞書の語に使う品詞と同じ)
- 除く語
  - 読みが MIN_READING_LENGTH 文字より短いか，MAX_READING_LENGTH 文字より長い．短い読みは既存の語と同じ読みになりやすく，
    長い読み(住所の全体，作品の題名)は普段の変換で打つことがまれなため
  - 表記が MAX_WORD_LENGTH 文字より長いか，ALLOWED_SYMBOLS 以外の記号・ほかの文字体系(ハングル・ギリシャ文字など)を含む
  - 表記が記号と数字だけ
  - 表記のかなが読みと合わない．表記のかなの部分は，その順に読みに現れなければならない(漢字・英字・数字の部分は 1 文字以上の読み．
    漢字に挟まれたケは漢字と同じに扱う)
  - 表記が英字だけ(と ALLOWED_SYMBOLS)で，英字を 1 文字ずつ読んだ読みでも，子音の並びが似た読み(tools/spelling.py)でもない
- 値(azooKey の値．大きいほどよく使う)は，既存の語より控えめにする
  - 品詞ごとに，worddict にある同じ品詞の語の値の BASE_QUANTILE の分位を基準にする
  - SudachiDict と NEologd のコスト(元の辞書のコストから作った 8000〜8999)が小さいほど，最大 SOURCE_COST_BONUS 上げる
  - 複数の UT 辞書にある語は，辞書が 1 つ増えるごとに MULTI_SOURCE_BONUS 上げる
  - 同じ読みの語が worddict にあれば，そのどれよりも SAME_READING_MARGIN 下げる．既存の候補の並びを変えず，そのあとに足すため
"""
import bz2
import collections
import pathlib
import re
import sys

# 同じディレクトリの spelling.py を読む(python3 -I ではスクリプトの場所が探す場所に入らないため)
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from spelling import similar, spelled_out  # noqa: E402

# 辞書の名前と品詞．同じ組が複数の辞書にあれば，先に書いた辞書の品詞にする(人名と地名の辞書の品詞のほうが細かいため)
SOURCES = [
    ("personal-names", "名詞,固有名詞,人名,一般,*,*,*"),
    ("place-names", "名詞,固有名詞,地域,一般,*,*,*"),
    ("sudachidict", "名詞,固有名詞,一般,*,*,*,*"),
    ("neologd", "名詞,固有名詞,一般,*,*,*,*"),
]
MIN_READING_LENGTH = 4
MAX_READING_LENGTH = 20
MAX_WORD_LENGTH = 20
BASE_QUANTILE = 0.1
SOURCE_COST_BONUS = 0.5
MULTI_SOURCE_BONUS = 0.3
SAME_READING_MARGIN = 1.0
# 英字の語を tools/spelling.py で比べるときの共通の部分の割合の下限(tools/fetch_wikidata.py と同じ)
SPELLING_THRESHOLD = 0.8
# 表記に入れてよい記号．名前によく使うものだけ
ALLOWED_SYMBOLS = set(" ・=-&'.!?")
MID_GENERAL = 501

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


def quantile(values, q):
    values = sorted(values)
    return values[int((len(values) - 1) * q)]


if len(sys.argv) != 5:
    sys.exit(__doc__)
worddict_path, ut_directory, ipadic_path, destination = sys.argv[1:]

ipadic = {}
for line in pathlib.Path(ipadic_path).read_bytes().decode("euc_jp").splitlines():
    number, feature = line.split(" ", 1)
    ipadic[feature] = int(number)

lines = []
existing = set()
lowest_by_reading = {}
values_by_cid = collections.defaultdict(list)
with open(worddict_path, encoding="utf-8") as file:
    for line in file:
        ruby, word, lcid, _, _, score = line.rstrip("\n").split("\t")
        lines.append(line)
        existing.add((ruby, word))
        value = float(score)
        lowest_by_reading[ruby] = min(lowest_by_reading.get(ruby, value), value)
        values_by_cid[int(lcid)].append(value)

# 読み・表記ごとに，品詞・UT のコストのうち最も小さいもの・載っている辞書の数
found = {}
skipped = collections.Counter()
read = collections.Counter()
for name, feature in SOURCES:
    cid = ipadic[feature]
    path = pathlib.Path(ut_directory) / f"mozcdic-ut-{name}.txt.bz2"
    seen = set()
    with bz2.open(path, "rt", encoding="utf-8") as file:
        for line in file:
            columns = line.rstrip("\n").split("\t")
            read[name] += 1
            if len(columns) != 5 or not columns[3].isdigit():
                skipped["形の正しくない行"] += 1
                continue
            reading, _, _, cost, word = columns
            reading = reading.translate(HIRAGANA_TO_KATAKANA)
            key = (reading, word)
            if key in existing:
                skipped["既にある"] += 1
                continue
            reason = problem(reading, word)
            if reason:
                skipped[reason] += 1
                continue
            if key in seen:
                continue
            seen.add(key)
            if key in found:
                previous_cid, previous_cost, sources = found[key]
                found[key] = (previous_cid, min(previous_cost, int(cost)), sources + 1)
            else:
                found[key] = (cid, int(cost), 1)

bases = {cid: quantile(values_by_cid[cid], BASE_QUANTILE) for _, feature in SOURCES for cid in [ipadic[feature]]}
added = []
capped = 0
for (reading, word), (cid, cost, sources) in sorted(found.items()):
    # UT のコストは 8000〜8999(元の辞書のコストから作った値)．人名は 8000，地名は 9000 で揃っている
    score = bases[cid] + SOURCE_COST_BONUS * min(1.0, max(0.0, (8999 - cost) / 999)) + MULTI_SOURCE_BONUS * (sources - 1)
    if reading in lowest_by_reading and score > lowest_by_reading[reading] - SAME_READING_MARGIN:
        score = lowest_by_reading[reading] - SAME_READING_MARGIN
        capped += 1
    added.append(f"{reading}\t{word}\t{cid}\t{cid}\t{MID_GENERAL}\t{score:.4f}\n")

with open(destination, "w", encoding="utf-8") as output:
    output.writelines(lines)
    output.writelines(added)

counts = collections.Counter(cid for cid, _, _ in found.values())
print(f"UT 辞書から足した語: {len(added)}(品詞ごと {dict(counts)}，同じ読みの語の下に置いた語 {capped})，読んだ行: {dict(read)}，"
      f"足さなかった行: {dict(skipped)}，基準の値: { {cid: round(value, 2) for cid, value in bases.items()} }", file=sys.stderr)
