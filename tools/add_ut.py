"""worddict に，Mozc UT 辞書(utuhiro78 さんの mozcdic-ut-*)の語を足す．

使い方:
    python3 -I tools/add_ut.py <worddict.tsv> <UT 辞書の置き場所> <IPAdic の left-id.def> <出力.tsv>

UT 辞書の置き場所には mozcdic-ut-<名前>.txt.bz2 を置く(tools/fetch_sources.sh が取得する)．1 行は Mozc の辞書と同じ
「読み(ひらがな)<TAB>左 ID<TAB>右 ID<TAB>コスト<TAB>表記」だが，ID はすべて 0000 で品詞は無い．

- 足すのは「読み・表記」の組が worddict に無いものだけ．既存の語の値は変えない
- 品詞(IPAdic の left-id)は辞書ごとに決める(SOURCES)．人名と地名の辞書はそれぞれの固有名詞，SudachiDict・NEologd・Wikipedia の
  見出し(jawiki)は品詞が分からないので「名詞,固有名詞,一般」(Hajime IME がユーザー辞書の語に使う品詞と同じ)，EDICT2(edict2)は
  ふつうの語が多いので「名詞,一般」．EDICT2 は表記がひらがなで終わる語(動詞・形容詞・句)を除く
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
import sys

# 同じディレクトリの wordfilter.py を読む(python3 -I ではスクリプトの場所が探す場所に入らないため)
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from wordfilter import HIRAGANA_TO_KATAKANA, problem  # noqa: E402

# 辞書の名前と品詞．同じ組が複数の辞書にあれば，先に書いた辞書の品詞にする(人名と地名の辞書の品詞のほうが細かいため)
SOURCES = [
    ("personal-names", "名詞,固有名詞,人名,一般,*,*,*"),
    ("place-names", "名詞,固有名詞,地域,一般,*,*,*"),
    ("sudachidict", "名詞,固有名詞,一般,*,*,*,*"),
    ("neologd", "名詞,固有名詞,一般,*,*,*,*"),
    ("jawiki", "名詞,固有名詞,一般,*,*,*,*"),
    ("edict2", "名詞,一般,*,*,*,*,*"),
]
# 名詞だけを足す辞書．EDICT2 は動詞・形容詞・句も含み品詞を持たないので，表記がひらがなで終わる語(愛おしがる・金づる)を除く
NOUNS_ONLY = {"edict2"}
BASE_QUANTILE = 0.1
SOURCE_COST_BONUS = 0.5
MULTI_SOURCE_BONUS = 0.3
SAME_READING_MARGIN = 1.0
MID_GENERAL = 501

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
            if not reason and name in NOUNS_ONLY and "\u3041" <= word[-1] <= "\u309f":
                reason = "ひらがなで終わる(名詞でない)"
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
