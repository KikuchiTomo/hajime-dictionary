"""azooKey の辞書に，Mozc の辞書(dictionary_oss)にしかない語を足した worddict を作る．

使い方:
    python3 -I tools/merge_mozc.py <azooKey の TSV> <Mozc の dictionary_oss> <IPAdic の left-id.def> <出力.tsv> [--penalty P]

- azooKey の TSV は tools/dump_azookey.py で書き出したもの．azooKey の語はすべて残す
- Mozc の語は「読み・語」の組が azooKey に無いものだけを足す
- 品詞: azooKey の cid は IPAdic(mecab-ipadic 2.7.0)の left-id と同じ番号．Mozc の id.def は独自の番号だが品詞の文字列は IPAdic 由来なので，
  文字列で IPAdic の番号に引き直す．7 列目(語彙)まで一致 → 7 列目を * にして一致 → 6 列目まで一致する最初のもの，の順に探し，
  どれにも当たらない品詞(「五段動詞」のように活用の行が決まっていないもの)の語は足さない
- コスト: Mozc は整数のコスト(大きいほどまれ)，azooKey は対数の確率に近い値(小さいほどまれ)．両方の辞書にある同じ品詞の語から，
  Mozc のコストの区間(BUCKET ごと)ごとに azooKey の値の中央値を求め，そのあいだを線形に補う．区間の外は端の値を使う．
  最後に --penalty を引く(Mozc だけの語はまれな語が多いので，既存の語より少し下げて試せるように)
- --min-reading-length より読みの短い Mozc だけの語は足さない
- 読みの表記ゆれを直すための行(6 列目が SPELLING_CORRECTION)は，わざと誤った読みなので足さない
"""
import argparse
import bisect
import collections
import pathlib
import statistics
import sys

BUCKET = 500
# 中央値を信じるのに要る語の数
MINIMUM_SAMPLES = 50
# 意味の ID(mid)．azooKey の MIDData に合わせる．品詞から決まらない語は「一般」
MID_GENERAL = 501
MID_BY_FEATURE = {
    "名詞,固有名詞,人名,姓": 344,
    "名詞,固有名詞,人名,名": 370,
    "名詞,固有名詞,組織": 378,
}

parser = argparse.ArgumentParser()
parser.add_argument("azookey")
parser.add_argument("mozc")
parser.add_argument("ipadic")
parser.add_argument("destination")
parser.add_argument("--penalty", type=float, default=0.0)
parser.add_argument("--min-reading-length", type=int, default=1)
arguments = parser.parse_args()


def load_ipadic(path):
    # mecab-ipadic の left-id.def は EUC-JP
    ids = {}
    for line in pathlib.Path(path).read_bytes().decode("euc_jp").splitlines():
        number, feature = line.split(" ", 1)
        ids[feature] = int(number)
    return ids


ipadic = load_ipadic(arguments.ipadic)
first_by_six = {}
for feature, number in ipadic.items():
    first_by_six.setdefault(tuple(feature.split(",")[:6]), number)


def to_ipadic(feature):
    if feature in ipadic:
        return ipadic[feature]
    fields = feature.split(",")
    general = ",".join(fields[:6] + ["*"])
    if general in ipadic:
        return ipadic[general]
    return first_by_six.get(tuple(fields[:6]))


mozc_directory = pathlib.Path(arguments.mozc)
mozc_ids = {}
for line in (mozc_directory / "id.def").read_text(encoding="utf-8").splitlines():
    number, feature = line.split(" ", 1)
    mozc_ids[int(number)] = to_ipadic(feature)
mid_of_cid = {}
for feature, number in ipadic.items():
    mid_of_cid[number] = next((mid for prefix, mid in MID_BY_FEATURE.items() if feature.startswith(prefix)), MID_GENERAL)

# ひらがな(ぁ〜ゖ)をカタカナにする．azooKey の読みはカタカナ
HIRAGANA_TO_KATAKANA = {code: code + 0x60 for code in range(0x3041, 0x3097)}

azookey = collections.defaultdict(list)
azookey_lines = []
with open(arguments.azookey, encoding="utf-8") as file:
    for line in file:
        ruby, word, lcid, rcid, _, score = line.rstrip("\n").split("\t")
        azookey[(ruby, word)].append((int(lcid), int(rcid), float(score)))
        azookey_lines.append(line)

skipped = collections.Counter()
mozc = []
for path in sorted(mozc_directory.glob("dictionary0*.txt")):
    for line in path.read_text(encoding="utf-8").splitlines():
        columns = line.split("\t")
        if len(columns) != 5:
            skipped["表記ゆれの補正"] += 1
            continue
        reading, lid, rid, cost, word = columns
        lcid, rcid = mozc_ids[int(lid)], mozc_ids[int(rid)]
        if lcid is None or rcid is None:
            skipped["対応する品詞が無い"] += 1
            continue
        mozc.append((reading.translate(HIRAGANA_TO_KATAKANA), word, lcid, rcid, int(cost)))

# 両方の辞書にある同じ品詞の語で，Mozc のコストと azooKey の値の対応を求める
samples = collections.defaultdict(list)
for ruby, word, lcid, rcid, cost in mozc:
    for azookey_lcid, azookey_rcid, score in azookey.get((ruby, word), []):
        if (azookey_lcid, azookey_rcid) == (lcid, rcid):
            samples[cost // BUCKET].append(score)
points = [(bucket * BUCKET + BUCKET / 2, statistics.median(scores)) for bucket, scores in sorted(samples.items()) if len(scores) >= MINIMUM_SAMPLES]
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
for ruby, word, lcid, rcid, cost in mozc:
    if (ruby, word) in azookey:
        continue
    # 短い読みは既存の語と同じ読みになりやすく，まれな語が候補を奪う(「じたい」が「次隊」になる)．足すのは長い読みの語だけにできる
    if len(ruby) < arguments.min_reading_length:
        continue
    key = (ruby, word, lcid, rcid)
    score = convert(cost) - arguments.penalty
    # Mozc の中で同じ語・品詞が重なっていれば，ありふれたほう(値の大きいほう)を残す
    if key not in added or added[key] < score:
        added[key] = score

with open(arguments.destination, "w", encoding="utf-8") as output:
    output.writelines(azookey_lines)
    for (ruby, word, lcid, rcid), score in added.items():
        output.write(f"{ruby}\t{word}\t{lcid}\t{rcid}\t{mid_of_cid.get(lcid, MID_GENERAL)}\t{score:.4f}\n")

print(f"azooKey: {len(azookey_lines)} 語，Mozc から足した語: {len(added)}，足さなかった行: {dict(skipped)}", file=sys.stderr)
print("コストの対応(Mozc のコスト → azooKey の値): " + ", ".join(f"{int(x)}→{y:.2f}" for x, y in points), file=sys.stderr)
