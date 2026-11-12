"""Wikidata(CC0)から，専門用語の辞書(terms.tsv)の分野ごとのクラスの項目の日本語の名前と読みを取り，一覧にする．

使い方:
    python3 -I tools/fetch_wikidata_terms.py <出力.tsv> [--raw <問い合わせの結果の置き場所.json>]

出力は sources/wikidata-terms.tsv としてリポジトリに入れる．辞書を作るときはこのファイルを使い，Wikidata には問い合わせない
(Wikidata は日々変わるので，同じ元のデータから同じ辞書ができるようにするため)．1 行は「読み<TAB>語<TAB>分野<TAB>項目」．

- 分野とクラスは tools/term_fields.py．クラスの項目(instance of)と下位のクラス(subclass of)を 2 段までたどって取る．
  際限なくたどると，上位の抽象的なクラスを通って関係の無い項目(数学に通貨や地名，物理学にバンド)が入るため
- 語は日本語のラベル．読みは，ラベルがカタカナ(・＝を含む)だけならラベル，そうでなければ「名前の読み」(P1814)．どちらも無い項目は使わない．
  カタカナのラベルに別の言い方の読み(「カーテンウォール」に「ちょうへき」)が付いた項目があるので，カタカナのラベルはラベルを読みにする
- 読みはカタカナをひらがなにし，空白・・＝を除いて，ひらがなと長音だけになるものを残す
- 論文・曖昧さ回避・分類群・Wikimedia の項目は除く
- --raw を付けると，問い合わせの結果をクラスごとにそのファイルに書き足し，次からは書いてあるクラスを問い合わせない
  (残す項目の決まりを試し直すため．問い合わせの回数の制限で止まっても続きから取るため)
"""
import json
import pathlib
import re
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from term_fields import FIELDS  # noqa: E402

# Wikidata Query Service．1 回の問い合わせは 60 秒まで．読みの分かる項目だけに絞ると，いちばん大きなクラス(化合物)でも 20 秒ほどで返る
ENDPOINT = "https://query.wikidata.org/sparql"
EXCLUDED_CLASSES = [
    "Q4167410",   # 曖昧さ回避
    "Q16521",     # 分類群
    "Q13442814",  # 論文
    "Q4167836",   # Wikimedia のカテゴリ
    "Q11266439",  # Wikimedia のテンプレート
    "Q13406463",  # Wikimedia の一覧
    "Q5",         # 人
    "Q8142",      # 通貨(単位のクラスの下にあり，物理学に入ってしまうため)
    "Q1643989",   # 法定通貨
]
QUERY = """
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?item ?label ?kana WHERE {
  { ?item wdt:P31|wdt:P279 wd:%(cls)s } UNION { ?item wdt:P31|wdt:P279 ?parent . ?parent wdt:P279 wd:%(cls)s }
  ?item rdfs:label ?label . FILTER(LANG(?label) = "ja")
  OPTIONAL { ?item wdt:P1814 ?kana }
  FILTER(BOUND(?kana) || REGEX(?label, "^[ァ-ヴー・＝]+$"))
  MINUS { ?item wdt:P31 ?excluded . VALUES ?excluded { %(excluded)s } }
}
"""
KATAKANA_LABEL = re.compile(r"^[ァ-ヴー・＝]+$")
READING = re.compile(r"^[ぁ-ゔー]+$")
SEPARATORS = str.maketrans("", "", " 　・＝")
TO_HIRAGANA = {c: c - 0x60 for c in range(0x30A1, 0x30F5)}


def ask(query):
    data = urllib.parse.urlencode({"query": query}).encode()
    request = urllib.request.Request(ENDPOINT, data=data, headers={"Accept": "application/sparql-results+json",
                                                                   "User-Agent": "hajime-dictionary-builder/1.0 (dictionary build script)"})
    attempts = 5
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                # ラベルに制御文字を含む項目があるので，文字列の中の制御文字を許して読む
                return json.loads(response.read().decode("utf-8"), strict=False)["results"]["bindings"]
        except Exception as error:  # noqa: BLE001
            if attempt == attempts - 1:
                raise
            print(f"問い合わせに失敗しました(やり直します): {error}", file=sys.stderr)
            time.sleep(min(30 * 2 ** attempt, 120))


def fetch(results, save):
    """クラスごとの問い合わせの結果(項目・ラベル・読み)．results にあるクラスは問い合わせない．1 つ取るたびに save を呼ぶ"""
    excluded = " ".join(f"wd:{q}" for q in EXCLUDED_CLASSES)
    for field in FIELDS:
        for cls in field.wikidata:
            if cls in results:
                continue
            rows = ask(QUERY % {"cls": cls, "excluded": excluded})
            results[cls] = [[row["item"]["value"].rsplit("/", 1)[1], row["label"]["value"], row.get("kana", {}).get("value")] for row in rows]
            print(f"{field.id} {cls}: {len(rows)} 件", file=sys.stderr)
            save(results)
            # 問い合わせの回数の制限に当たらないよう間を空ける
            time.sleep(5)
    return results


def reading_of(label, kana):
    source = label if KATAKANA_LABEL.match(label) else kana
    if not source:
        return None
    reading = source.translate(SEPARATORS).translate(TO_HIRAGANA)
    return reading if READING.match(reading) else None


def terms(results):
    """(読み, 語, 分野, 項目) の並び．同じ読みと語と分野は 1 つにする"""
    seen = set()
    for field in FIELDS:
        for cls in field.wikidata:
            for item, label, kana in results.get(cls, []):
                reading = reading_of(label, kana)
                if not reading or "\t" in label or "\n" in label:
                    continue
                key = (reading, label, field.id)
                if key in seen:
                    continue
                seen.add(key)
                yield reading, label, field.id, item


def main():
    if len(sys.argv) not in (2, 4) or (len(sys.argv) == 4 and sys.argv[2] != "--raw"):
        sys.exit(__doc__)
    output = pathlib.Path(sys.argv[1])
    raw = pathlib.Path(sys.argv[3]) if len(sys.argv) == 4 else None
    results = json.loads(raw.read_text(encoding="utf-8")) if raw and raw.exists() else {}

    def save(partial):
        if raw:
            raw.write_text(json.dumps(partial, ensure_ascii=False), encoding="utf-8")

    results = fetch(results, save)
    rows = sorted(terms(results), key=lambda row: (row[0].encode(), row[1].encode(), row[2]))
    with output.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write("\t".join(row) + "\n")
    print(f"書きました: {output}({len(rows)} 行)", file=sys.stderr)


if __name__ == "__main__":
    main()
