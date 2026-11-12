"""worddict に，mecab-ipadic-NEologd の元のデータ(seed)の語を足す．

使い方:
    python3 -I tools/add_neologd.py <worddict.tsv> <NEologd の seed の置き場所> <IPAdic の left-id.def> <出力.tsv>

seed の置き場所には neologd/*.csv.xz を置く(tools/fetch_sources.sh が sources/sources.txt に従って取得する)．
1 行は MeCab の辞書の形「表記,左 ID,右 ID,コスト,品詞 1〜6,原形,読み,発音」．ID は mecab-ipadic の番号で，azooKey の cid と同じ番号．

- 足すのは「読み・表記」の組が worddict に無いものだけ．既存の語の値は変えない
- 品詞は seed の左 ID・右 ID をそのまま使う．IPAdic の left-id.def の品詞と seed の品詞 1〜6 が合わない行は足さない
- 除く語の決まりは tools/wordfilter.py(Mozc UT 辞書と同じ)
- 値: 両方の辞書にある同じ品詞の語で，NEologd のコストの区間ごとに azooKey の値の中央値を求め，そのあいだを線形に補う(tools/merge_mozc.py と同じ)．
  NEologd だけの語はまれな語が多いので PENALTY を引き，同じ読みの語が worddict にあれば，そのどれよりも SAME_READING_MARGIN 下げる．
  既存の候補の並びを変えず，そのあとに足すため
"""
import bisect
import collections
import csv
import lzma
import pathlib
import statistics
import sys

# 同じディレクトリの wordfilter.py を読む(python3 -I ではスクリプトの場所が探す場所に入らないため)
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from wordfilter import problem  # noqa: E402

BUCKET = 500
# 中央値を信じるのに要る語の数
MINIMUM_SAMPLES = 50
PENALTY = 1.0
SAME_READING_MARGIN = 1.0
MID_GENERAL = 501

if len(sys.argv) != 5:
    sys.exit(__doc__)
worddict_path, seed_directory, ipadic_path, destination = sys.argv[1:]

# IPAdic の番号ごとの品詞 1〜6
ipadic = {}
for line in pathlib.Path(ipadic_path).read_bytes().decode("euc_jp").splitlines():
    number, feature = line.split(" ", 1)
    ipadic[int(number)] = feature.split(",")[:6]

lines = []
existing = collections.defaultdict(list)
lowest_by_reading = {}
with open(worddict_path, encoding="utf-8") as file:
    for line in file:
        lines.append(line)
        columns = line.rstrip("\n").split("\t")
        if len(columns) < 6:
            continue
        ruby, word, lcid, rcid, value = columns[0], columns[1], int(columns[2]), int(columns[3]), float(columns[5])
        existing[(ruby, word)].append((lcid, rcid, value))
        lowest_by_reading[ruby] = min(lowest_by_reading.get(ruby, value), value)

skipped = collections.Counter()
rows = []
for path in sorted(pathlib.Path(seed_directory).glob("*.csv.xz")):
    with lzma.open(path, "rt", encoding="utf-8", errors="replace") as file:
        for columns in csv.reader(file):
            if len(columns) < 12 or not columns[1].lstrip("-").isdigit() or not columns[2].lstrip("-").isdigit():
                skipped["形の正しくない行"] += 1
                continue
            word, lid, rid, cost, reading = columns[0], int(columns[1]), int(columns[2]), columns[3], columns[11]
            if ipadic.get(lid) != columns[4:10] or rid not in ipadic or not cost.lstrip("-").isdigit():
                skipped["品詞が IPAdic と合わない"] += 1
                continue
            rows.append((reading, word, lid, rid, int(cost)))

# 両方の辞書にある同じ品詞の語で，NEologd のコストと azooKey の値の対応を求める
samples = collections.defaultdict(list)
for reading, word, lid, rid, cost in rows:
    for lcid, rcid, value in existing.get((reading, word), []):
        if (lcid, rcid) == (lid, rid):
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
capped = 0
for reading, word, lid, rid, cost in rows:
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
    key = (reading, word, lid, rid)
    # 同じ語・品詞が重なっていれば，ありふれたほう(値の大きいほう)を残す
    if key not in added or added[key] < score:
        added[key] = score

with open(destination, "w", encoding="utf-8") as output:
    output.writelines(lines)
    for (reading, word, lid, rid), score in sorted(added.items()):
        output.write(f"{reading}\t{word}\t{lid}\t{rid}\t{MID_GENERAL}\t{score:.4f}\n")

counts = collections.Counter(" ".join(ipadic[lid][:2]) for _, _, lid, _ in added)
print(f"NEologd から足した語: {len(added)}(品詞ごと {dict(counts.most_common(6))})，読んだ行: {len(rows)}，足さなかった行: {dict(skipped)}",
      file=sys.stderr)
print("コストの対応(NEologd のコスト → azooKey の値): " + ", ".join(f"{int(x)}→{y:.2f}" for x, y in points), file=sys.stderr)
