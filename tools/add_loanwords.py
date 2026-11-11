"""worddict に，外来語の英字の綴り(sources/wikidata-loanwords.tsv)を足す．「レッドハット」→ Red Hat，「にゅーらる」→ neural．

使い方:
    python3 -I tools/add_loanwords.py <worddict.tsv> <wikidata-loanwords.tsv> <IPAdic の left-id.def> <出力.tsv>

- 読みは一覧の読みのほか，打ち方の揺れも足す: ヴ → ブ(ヴァ → バ など)，トゥ → ツ(ウブントゥ → ウブンツ)，4 文字以上で末尾の長音を除いたもの(サーバー → サーバ)
- 足すのは「読み・綴り」の組が worddict に無く，次のどちらかに当たるものだけ
  - 同じ読みのカタカナ語(読みそのもの)が worddict にある(英字はそのカタカナ語の別の書き方)
  - 読みが worddict に無いか，英字の語しか無い(新しいカタカナ語)
  カタカナ語が無く，かなや漢字の語がある読み(「サンサイ」→ 山菜)には足さない．日本語の語の候補に英字が混ざるため
- 品詞: 一般の語は「名詞,一般」，人は「名詞,固有名詞,人名,一般」，ほかは「名詞,固有名詞,一般」
- 揺れの読みは，固有名詞と人では読みが worddict に無いときだけ足す(「サーヴァ」(Sava)を「サーバ」(server)の読みに足さないため)
- コスト(azooKey の値．大きいほどよく使う)．揺れの読みは，さらに VARIANT_PENALTY 下げる
  - 同じ綴りが別のカタカナの読みで worddict にあれば，その値から VARIANT_PENALTY 下げる(「ウブントゥ」の Ubuntu から「ウブンツ」の Ubuntu)
  - 同じ読みのカタカナ語があれば，その語より KATAKANA_MARGIN 下げる．カタカナを先に出し，英字はその次に選べるようにする
  - どちらも無ければ，worddict にある「カタカナの読みで英字の語」の値の中央値から NEW_READING_PENALTY 下げ，言語版の数が多いほど少し上げる
"""
import collections
import math
import pathlib
import statistics
import sys

KATAKANA_MARGIN = 2.0
VARIANT_PENALTY = 0.5
# 揺れの読みも含めて，読みがこれより短い語は足さない(短い読みは文の中のかなと重なりやすい)
MIN_READING_LENGTH = 3
NEW_READING_PENALTY = 1.0
# 言語版の数が 10 倍になるごとに上げる値と，その上限
LINKS_BONUS_PER_DECADE = 0.3
MAXIMUM_LINKS_BONUS = 0.9
MID_GENERAL = 501
FEATURES = {
    "common": "名詞,一般,*,*,*,*,*",
    "proper": "名詞,固有名詞,一般,*,*,*,*",
    "person": "名詞,固有名詞,人名,一般,*,*,*",
}

if len(sys.argv) != 5:
    sys.exit(__doc__)
worddict_path, loanwords_path, ipadic_path, destination = sys.argv[1:]

ipadic = {}
for line in pathlib.Path(ipadic_path).read_bytes().decode("euc_jp").splitlines():
    number, feature = line.split(" ", 1)
    ipadic[feature] = int(number)
cids = {kind: ipadic[feature] for kind, feature in FEATURES.items()}


def is_katakana(text):
    return all(0x30A1 <= ord(c) <= 0x30FA or c == "ー" for c in text)


def is_latin(text):
    return all(c.isascii() for c in text) and any(c.isalpha() for c in text)


lines = []
existing = set()
words_by_reading = collections.defaultdict(list)
latin_scores = []
# 英字の語の，カタカナの読みでの値のうちいちばん大きいもの
known_latin = {}
with open(worddict_path, encoding="utf-8") as file:
    for line in file:
        ruby, word, _, _, _, score = line.rstrip("\n").split("\t")
        lines.append(line)
        existing.add((ruby, word))
        words_by_reading[ruby].append((word, float(score)))
        if is_katakana(ruby) and is_latin(word):
            latin_scores.append(float(score))
            known_latin[word] = max(known_latin.get(word, float("-inf")), float(score))
base = statistics.median(latin_scores) - NEW_READING_PENALTY


def variants(reading):
    result = {reading}
    voiced = reading
    for before, after in [("ヴァ", "バ"), ("ヴィ", "ビ"), ("ヴェ", "ベ"), ("ヴォ", "ボ"), ("ヴ", "ブ")]:
        voiced = voiced.replace(before, after)
    result.add(voiced)
    for value in list(result):
        result.add(value.replace("トゥ", "ツ"))
    for value in list(result):
        if len(value) >= 4 and value.endswith("ー") and not value.endswith("ーー"):
            result.add(value[:-1])
    return sorted(result)


added = {}
skipped = collections.Counter()
with open(loanwords_path, encoding="utf-8") as file:
    for line in file:
        if line.startswith("#"):
            continue
        reading, word, kind, links, _ = line.rstrip("\n").split("\t")
        for ruby in variants(reading):
            if len(ruby) < MIN_READING_LENGTH:
                skipped["読みが短い"] += 1
                continue
            if (ruby, word) in existing or (ruby, word, kind) in added:
                skipped["既にある"] += 1
                continue
            present = words_by_reading.get(ruby, [])
            katakana = [score for text, score in present if text == ruby]
            if not katakana and any(not is_latin(text) for text, _ in present):
                skipped["かなや漢字の語の読み"] += 1
                continue
            variant = ruby != reading
            if variant and kind != "common" and present:
                skipped["固有名詞の揺れの読みが既にある"] += 1
                continue
            if word in known_latin:
                score = known_latin[word] - VARIANT_PENALTY
            elif katakana:
                score = max(katakana) - KATAKANA_MARGIN
            else:
                score = base + min(MAXIMUM_LINKS_BONUS, LINKS_BONUS_PER_DECADE * math.log10(1 + int(links)))
            if variant:
                score -= VARIANT_PENALTY
            added[(ruby, word, kind)] = score

# 同じ読みと綴りが種類違いで重なったら，値の大きいほうを残す
best = {}
for (ruby, word, kind), score in added.items():
    if (ruby, word) not in best or best[(ruby, word)][1] < score:
        best[(ruby, word)] = (kind, score)

with open(destination, "w", encoding="utf-8") as output:
    output.writelines(lines)
    for (ruby, word), (kind, score) in sorted(best.items()):
        cid = cids[kind]
        output.write(f"{ruby}\t{word}\t{cid}\t{cid}\t{MID_GENERAL}\t{score:.4f}\n")

counts = collections.Counter(kind for kind, _ in best.values())
print(f"外来語の英字の綴りを足した語: {len(best)} {dict(counts)}，足さなかったもの: {dict(skipped)}，新しい読みの基準の値: {base:.2f}", file=sys.stderr)
