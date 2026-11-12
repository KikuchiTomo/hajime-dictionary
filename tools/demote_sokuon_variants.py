"""促音を落とした読みの揺れ(決して → ケシテ)の値を下げる．

使い方:
    python3 -I tools/demote_sokuon_variants.py <worddict.tsv> <出力.tsv>

同じ表記に，読み R と，R にッを 1 つ足した読み R'(決して の ケシテ と ケッシテ)があり，R' のほうが値が大きい(よく使われる)とき，
R は促音を落として打ったときのための揺れとみなし，R の値を DEMOTION だけ下げる．揺れの読みが同じ読みのふつうの語
(「けして」の「消して」，「しけ」の「時化」)より先に出ないようにするため．語は消さないので，候補から選べ，Zenzai も使える．
R のほうが値が大きい組(欲し の ホシ と ホッシ)は，ッのある読みのほうが揺れなので変えない．

下げた語と同じ読み・同じ品詞で，表記が読みのかなそのものの語(決して に対する 副詞の けして)も一緒に下げる．
かなの語どうしは別の語のことが多いので(バタ と バッタ)，かなの語だけで組を作ることはしない．
"""
import collections
import sys

DEMOTION = 5.0
SOKUON = "ッ"
KATAKANA_TO_HIRAGANA = {code: code - 0x60 for code in range(0x30A1, 0x30F7)}


def variants(reading):
    """読みからッを 1 つ除いた読み"""
    return {reading[:i] + reading[i + 1:] for i, character in enumerate(reading) if character == SOKUON}


def is_kana_of(word, reading):
    """表記が読みのかなそのもの(カタカナの読みか，そのひらがな)か"""
    return word in (reading, reading.translate(KATAKANA_TO_HIRAGANA))


source, destination = sys.argv[1:3]
lines = open(source, encoding="utf-8").read().splitlines(keepends=True)
entries = []
for line in lines:
    columns = line.rstrip("\n").split("\t")
    entries.append(columns if len(columns) >= 6 else None)

# 表記ごとに，読みとその値のうち最も大きいもの(かなの表記の語は組を作らないので入れない)
readings_by_word = collections.defaultdict(dict)
for columns in entries:
    if columns is None or is_kana_of(columns[1], columns[0]):
        continue
    reading, word, value = columns[0], columns[1], float(columns[5])
    readings_by_word[word][reading] = max(value, readings_by_word[word].get(reading, float("-inf")))

demoted = set()
for word, readings in readings_by_word.items():
    for full, full_value in readings.items():
        for short in variants(full):
            if len(short) >= 2 and short in readings and readings[short] < full_value:
                demoted.add((short, word))
# 下げた語の読みと品詞．同じ読み・品詞のかなの表記の語も下げる
demoted_classes = {(columns[0], columns[2]) for columns in entries if columns is not None and (columns[0], columns[1]) in demoted}

changed = 0
with open(destination, "w", encoding="utf-8") as output:
    for line, columns in zip(lines, entries):
        if columns is not None and ((columns[0], columns[1]) in demoted
                                    or (is_kana_of(columns[1], columns[0]) and (columns[0], columns[2]) in demoted_classes)):
            columns[5] = f"{float(columns[5]) - DEMOTION:.4f}"
            line = "\t".join(columns) + "\n"
            changed += 1
        output.write(line)

print(f"促音を落とした読みの揺れの値を下げた語: {len(demoted)}，同じ読み・品詞のかなの語を含めた行: {changed}", file=sys.stderr)
