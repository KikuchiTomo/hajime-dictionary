"""worddict に，SudachiDict の元のデータ(small_lex・core_lex・notcore_lex)の名詞を足す．

使い方:
    python3 -I tools/add_sudachi.py <worddict.tsv> <SudachiDict の置き場所> <IPAdic の left-id.def> <Unihan.zip> <出力.tsv>

置き場所には sudachidict/*_lex.zip を置く(tools/fetch_sources.sh が sources/sources.txt に従って取得する)．
1 行は「見出し(解析用),左 ID,右 ID,コスト,見出し,品詞 1〜6,読み,…」．品詞は UniDic の体系で，azooKey(IPAdic)の品詞と違う．

- 足すのは名詞だけ．品詞を NOUN_FEATURES で IPAdic の品詞に引き直す(動詞・形容詞は活用の型の対応が要るので足さない)
- 足すのは「読み・表記」の組が worddict に無いものだけ．既存の語の値は変えない．除く語の決まりは tools/wordfilter.py と
  tools/brokenwords.py(常用漢字は Unihan データベースから読む)
- 値: 両方の辞書にある同じ品詞の語で，SudachiDict のコストの区間ごとに azooKey の値の中央値を求め，そのあいだを線形に補う．
  PENALTY を引き，同じ読みの語が worddict にあれば，そのどれよりも SAME_READING_MARGIN 下げる(既存の候補の並びを変えないため)
"""
import bisect
import collections
import csv
import io
import pathlib
import statistics
import sys
import zipfile

# 同じディレクトリの wordfilter.py と brokenwords.py を読む(python3 -I ではスクリプトの場所が探す場所に入らないため)
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from brokenwords import SameReadingWords, broken, load_joyo  # noqa: E402
from wordfilter import problem  # noqa: E402

BUCKET = 1000
MINIMUM_SAMPLES = 50
PENALTY = 1.0
SAME_READING_MARGIN = 1.0
MID_GENERAL = 501
# SudachiDict(UniDic)の名詞の品詞 1〜4 → IPAdic の品詞．載っていない品詞(数詞・助数詞など)の語は足さない
NOUN_FEATURES = {
    ("名詞", "固有名詞", "人名", "姓"): "名詞,固有名詞,人名,姓,*,*,*",
    ("名詞", "固有名詞", "人名", "名"): "名詞,固有名詞,人名,名,*,*,*",
    ("名詞", "固有名詞", "人名", "一般"): "名詞,固有名詞,人名,一般,*,*,*",
    ("名詞", "固有名詞", "地名", "国"): "名詞,固有名詞,地域,国,*,*,*",
    ("名詞", "固有名詞", "地名", "一般"): "名詞,固有名詞,地域,一般,*,*,*",
    ("名詞", "固有名詞", "一般", "*"): "名詞,固有名詞,一般,*,*,*,*",
    ("名詞", "普通名詞", "一般", "*"): "名詞,一般,*,*,*,*,*",
    ("名詞", "普通名詞", "サ変可能", "*"): "名詞,サ変接続,*,*,*,*,*",
    ("名詞", "普通名詞", "サ変形状詞可能", "*"): "名詞,サ変接続,*,*,*,*,*",
    ("名詞", "普通名詞", "形状詞可能", "*"): "名詞,形容動詞語幹,*,*,*,*,*",
    ("名詞", "普通名詞", "副詞可能", "*"): "名詞,副詞可能,*,*,*,*,*",
}
FILES = ["small_lex", "core_lex", "notcore_lex"]

if len(sys.argv) != 6:
    sys.exit(__doc__)
worddict_path, sudachi_directory, ipadic_path, unihan_path, destination = sys.argv[1:]
joyo = load_joyo(unihan_path)

ipadic = {}
for line in pathlib.Path(ipadic_path).read_bytes().decode("euc_jp").splitlines():
    number, feature = line.split(" ", 1)
    ipadic[feature] = int(number)
cid_of = {key: ipadic[feature] for key, feature in NOUN_FEATURES.items()}

feature_of_cid = {number: feature for feature, number in ipadic.items()}
lines = []
existing = collections.defaultdict(list)
lowest_by_reading = {}
same_reading = SameReadingWords()
with open(worddict_path, encoding="utf-8") as file:
    for line in file:
        lines.append(line)
        columns = line.rstrip("\n").split("\t")
        if len(columns) < 6:
            continue
        ruby, word, lcid, value = columns[0], columns[1], int(columns[2]), float(columns[5])
        existing[(ruby, word)].append((lcid, value))
        lowest_by_reading[ruby] = min(lowest_by_reading.get(ruby, value), value)
        same_reading.add(ruby, word, value, feature_of_cid.get(lcid, ""))

skipped = collections.Counter()
rows = []
for name in FILES:
    with zipfile.ZipFile(pathlib.Path(sudachi_directory) / f"{name}.zip") as archive:
        with archive.open(f"{name}.csv") as raw:
            reader = csv.reader(io.TextIOWrapper(raw, encoding="utf-8"))
            next(reader)
            for columns in reader:
                if len(columns) < 12 or not columns[3].lstrip("-").isdigit():
                    skipped["形の正しくない行"] += 1
                    continue
                cid = cid_of.get(tuple(columns[5:9]))
                if cid is None:
                    skipped["名詞でない(対応する品詞が無い)"] += 1
                    continue
                word, reading, cost = columns[4] or columns[0], columns[11], int(columns[3])
                # 左 ID が -1 の行は解析に使わない見出し(分割した語の参照)なので足さない
                if columns[1] == "-1":
                    skipped["解析に使わない見出し"] += 1
                    continue
                rows.append((reading, word, cid, cost))

samples = collections.defaultdict(list)
for reading, word, cid, cost in rows:
    for lcid, value in existing.get((reading, word), []):
        if lcid == cid:
            samples[cost // BUCKET].append(value)
points = [(bucket * BUCKET + BUCKET / 2, statistics.median(values)) for bucket, values in sorted(samples.items())
          if len(values) >= MINIMUM_SAMPLES]
if len(points) < 2:
    sys.exit("コストの対応を求めるのに足りる語がありません")
costs = [cost for cost, _ in points]


def convert(cost):
    index = bisect.bisect_left(costs, cost)
    if index == 0:
        return points[0][1]
    if index == len(points):
        return points[-1][1]
    (x0, y0), (x1, y1) = points[index - 1], points[index]
    return y0 + (y1 - y0) * (cost - x0) / (x1 - x0)


added = {}
removed = collections.defaultdict(set)
names = {ipadic[feature] for feature in NOUN_FEATURES.values() if feature.startswith("名詞,固有名詞,人名")}
for reading, word, cid, cost in rows:
    if (reading, word) in existing:
        skipped["既にある"] += 1
        continue
    reason = problem(reading, word)
    if reason:
        skipped[reason] += 1
        continue
    score = convert(cost) - PENALTY
    if reading in lowest_by_reading and score > lowest_by_reading[reading] - SAME_READING_MARGIN:
        score = lowest_by_reading[reading] - SAME_READING_MARGIN
    key = (reading, word, cid)
    reason = broken(reading, word, score, same_reading, joyo, name=cid in names)
    if reason:
        removed[reason].add(key)
        continue
    if key not in added or added[key] < score:
        added[key] = score

with open(destination, "w", encoding="utf-8") as output:
    output.writelines(lines)
    for (reading, word, cid), score in sorted(added.items()):
        output.write(f"{reading}\t{word}\t{cid}\t{cid}\t{MID_GENERAL}\t{score:.4f}\n")

counts = collections.Counter(cid for _, _, cid in added)
print(f"SudachiDict から足した語: {len(added)}(品詞ごと {dict(counts.most_common(8))})，読んだ名詞の行: {len(rows)}，"
      f"足さなかった行: {dict(skipped)}，壊れた書き方として除いた語: { {reason: len(keys - added.keys()) for reason, keys in removed.items()} }",
      file=sys.stderr)
print("コストの対応(SudachiDict のコスト → azooKey の値): " + ", ".join(f"{int(x)}→{y:.2f}" for x, y in points[:12]), file=sys.stderr)
