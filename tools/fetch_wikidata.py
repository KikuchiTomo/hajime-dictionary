"""Wikidata(CC0)から，日本語の名前がカタカナの項目と英語の名前の組を取り，外来語の英字の綴りの一覧にする．

使い方:
    python3 -I tools/fetch_wikidata.py <出力.tsv> [--raw <問い合わせの結果の置き場所.json>]

出力は sources/wikidata-loanwords.tsv としてリポジトリに入れる．辞書を作るときはこのファイルを使い，Wikidata には問い合わせない
(Wikidata は日々変わるので，同じ元のデータから同じ辞書ができるようにするため)．1 行は「読み<TAB>英字の綴り<TAB>種類<TAB>言語版の数<TAB>項目」．

- 問い合わせ先は QLever の Wikidata(https://qlever.dev/api/wikidata)．日本語のラベルか別名がカタカナ(・＝を含む)だけの項目の，英語のラベルを取る
- 読みは日本語の名前から・＝を除いたもの(カタカナ)
- 種類は common(英語のラベルが小文字で始まる一般の語)，person(人)，proper(そのほかの固有名詞)
- 残す項目
  - 曖昧さ回避・生物の分類群・論文・Wikimedia のカテゴリなどの項目は除く
  - 英語のラベルは英字・空白・「.&'+-」だけで，4 語まで
  - カタカナと英語の綴りの子音の並びが似ていて(共通の部分の割合が THRESHOLD 以上)，最初と最後の子音が同じもの．
    同じ項目でも名前の違う別の物(「ニューラルネットワーク」と「artificial neural network」)を除くため
  - 人は，日本語の名前の・＝の区切りと英語の語の数が同じもの
  - 言語版(sitelinks)の数が，一般の語は 1 以上，人は MIN_LINKS_PERSON 以上，そのほかの固有名詞は MIN_LINKS_PROPER 以上．よく知られた名前を残すため
- --raw を付けると，問い合わせの結果をそのファイルに書き，次からはそれを読んで問い合わせない(残す項目の決まりを試し直すため)
- 日本語の名前が・＝で区切られ，英語の語の数と同じなら，語ごとの組も作る(「ニューラル・ネットワーク」→ ニューラル と neural)．
  まれな組を除くため，一般の語から作った組か，PIECE_MIN_ITEMS 個以上の項目から作られた組だけを残す
"""
import collections
import json
import math
import re
import sys
import time
import urllib.parse
import urllib.request

ENDPOINT = "https://qlever.dev/api/wikidata"
THRESHOLD = 0.8
MIN_LINKS_PROPER = 15
MIN_LINKS_PERSON = 50
PIECE_MIN_ITEMS = 2
MIN_READING_LENGTH = 3
# 1 回の問い合わせが QLever の時間の上限に収まるよう，日本語の名前の先頭の文字で分ける
PARTITIONS = ["ァ-ア", "ィ-イ", "ゥ-ウ", "ェ-エ", "ォ-オ", "カ-ゴ", "サ-ゾ", "タ-ド", "ナ-ノ", "ハ-ボ", "パ-ポ", "マ-モ", "ャ-ヨ", "ラ-ロ", "ヮ-ヴー・＝"]
HUMAN = "Q5"
EXCLUDED_CLASSES = [
    "Q4167410",   # 曖昧さ回避
    "Q16521",     # 分類群
    "Q13442814",  # 論文
    "Q4167836",   # Wikimedia のカテゴリ
    "Q11266439",  # Wikimedia のテンプレート
    "Q13406463",  # Wikimedia の一覧
    "Q17633526",  # Wikinews の記事
    "Q22808320",  # Wikimedia の人名の曖昧さ回避
]
ENGLISH_LABEL = re.compile(r"^[A-Za-z][A-Za-z .&'+-]*$")
KATAKANA_NAME = "[ァ-ヴー・＝]"

if len(sys.argv) not in (2, 4) or (len(sys.argv) == 4 and sys.argv[2] != "--raw"):
    sys.exit(__doc__)
raw_path = sys.argv[3] if len(sys.argv) == 4 else None


def query(sparql):
    url = ENDPOINT + "?" + urllib.parse.urlencode({"query": sparql})
    request = urllib.request.Request(url, headers={"Accept": "text/tab-separated-values", "User-Agent": "hajime-dictionary"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=600) as response:
                text = response.read().decode("utf-8")
            lines = text.split("\n")
            # 時間切れのときは，途中まで書いたあとに知らせが付く
            if lines[0].startswith("?") and "An error has occurred" not in text:
                return [line.split("\t") for line in lines[1:] if line]
        except OSError:
            pass
        time.sleep(30 * (attempt + 1))
    sys.exit("問い合わせに失敗しました")


def entity(value):
    return value.strip("<>").rsplit("/", 1)[1]


LITERAL = re.compile(r'^"(.*)"(?:@[A-Za-z-]+|\^\^<[^>]*>)?$')


def literal(value):
    """TSV の値(「"ボストン"@ja」「217」「"217"^^<…#int>」)の中身．読めなければ None"""
    match = LITERAL.match(value)
    if not match:
        return value if re.fullmatch(r"-?\d+", value) else None
    try:
        return json.loads('"' + match.group(1) + '"')
    except ValueError:
        return None


PREFIXES = """PREFIX wikibase: <http://wikiba.se/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wd: <http://www.wikidata.org/entity/>
"""

pairs = []
classes = collections.defaultdict(set)
class_values = " ".join(f"wd:{q}" for q in [HUMAN] + EXCLUDED_CLASSES)
raw = None
if raw_path:
    try:
        with open(raw_path, encoding="utf-8") as file:
            raw = json.load(file)
    except FileNotFoundError:
        pass
if raw:
    pairs = [tuple(pair) for pair in raw["pairs"]]
    for item, values in raw["classes"].items():
        classes[item] = set(values)
for partition in [] if raw else PARTITIONS:
    for predicate in ["rdfs:label", "skos:altLabel"]:
        name_filter = f'?item {predicate} ?ja . FILTER(LANG(?ja)="ja") FILTER(REGEX(?ja, "^[{partition}]{KATAKANA_NAME}*$"))'
        rows = query(PREFIXES + f"""SELECT ?item ?ja ?en ?links WHERE {{
  {name_filter}
  ?item rdfs:label ?en . FILTER(LANG(?en)="en")
  ?item wikibase:sitelinks ?links .
}}""")
        for item, ja, en, links in rows:
            values = literal(ja), literal(en), literal(links)
            if None not in values:
                pairs.append((entity(item), values[0], values[1], int(values[2])))
        rows = query(PREFIXES + f"""SELECT DISTINCT ?item ?class WHERE {{
  {name_filter}
  VALUES ?class {{ {class_values} }}
  ?item wdt:P31 ?class .
}}""")
        for item, value in rows:
            classes[entity(item)].add(entity(value))
        print(f"{partition} {predicate}: {len(pairs)} 組", file=sys.stderr)
if raw_path and not raw:
    with open(raw_path, "w", encoding="utf-8") as file:
        json.dump({"pairs": pairs, "classes": {item: sorted(values) for item, values in classes.items()}}, file, ensure_ascii=False)

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


def similar(katakana, english):
    a = skeleton("".join(KANA.get(c, "") for c in katakana), False)
    b = skeleton(english, True)
    if min(len(a), len(b)) < 2 or a[0] != b[0] or a[-1] != b[-1]:
        return False
    return 2 * common_length(a, b) / (len(a) + len(b)) >= THRESHOLD


chosen = {}
pieces = collections.defaultdict(lambda: {"items": set(), "kind": "proper", "links": 0})
for item, ja, en, links in pairs:
    item_classes = classes.get(item, set())
    if item_classes & set(EXCLUDED_CLASSES):
        continue
    if not ENGLISH_LABEL.match(en) or len(en.split()) > 4:
        continue
    kind = "person" if HUMAN in item_classes else "common" if en[0].islower() else "proper"
    minimum = {"common": 1, "person": MIN_LINKS_PERSON, "proper": MIN_LINKS_PROPER}[kind]
    if links < minimum or not similar(ja, en):
        continue
    names = [part for part in re.split("[・＝]", ja) if part]
    words = en.replace("-", " ").split()
    # 人は，日本語の名前の区切りと英語の語の数が合うものだけ(名字だけの「ゴルドーニ」を「Carlo Goldoni」にしない)
    if kind == "person" and len(names) != len(words):
        continue
    reading = ja.replace("・", "").replace("＝", "")
    if len(reading) < MIN_READING_LENGTH:
        continue
    key = (reading, en)
    if key not in chosen or chosen[key][1] < links:
        chosen[key] = (kind, links, item)
    if len(names) == len(words) > 1:
        for name, word in zip(names, words):
            if len(name) >= MIN_READING_LENGTH and similar(name, word):
                piece = pieces[(name, word)]
                piece["items"].add(item)
                piece["links"] = max(piece["links"], links)
                if kind == "common":
                    piece["kind"] = "common"
                elif kind == "person" and piece["kind"] != "common":
                    piece["kind"] = "person"

for (name, word), piece in pieces.items():
    if (name, word) in chosen:
        continue
    if piece["kind"] == "common" or len(piece["items"]) >= PIECE_MIN_ITEMS:
        chosen[(name, word)] = (piece["kind"], piece["links"], min(piece["items"]))

with open(sys.argv[1], "w", encoding="utf-8") as output:
    output.write(f"# Wikidata(CC0)の日本語の名前(カタカナ)と英語の名前．tools/fetch_wikidata.py が {time.strftime('%Y-%m-%d')} に作った．"
                 "読み<TAB>英字の綴り<TAB>種類<TAB>言語版の数<TAB>項目\n")
    for (reading, word), (kind, links, item) in sorted(chosen.items()):
        output.write(f"{reading}\t{word}\t{kind}\t{links}\t{item}\n")
counts = collections.Counter(kind for kind, _, _ in chosen.values())
print(f"{len(chosen)} 組を書きました: {dict(counts)}", file=sys.stderr)
