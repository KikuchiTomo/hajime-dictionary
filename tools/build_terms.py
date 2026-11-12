"""専門用語の辞書(terms.tsv)を作る．通常の辞書に無い語を，分野を付けて並べる．

使い方:
    python3 -I tools/build_terms.py <worddict.tsv> <JMdict の JSON(jmdict-simplified の .json.tgz)> <wikidata-terms.tsv> <出力 terms.tsv>

出力の 1 行は「読み<TAB>語<TAB>品詞<TAB>分野<TAB>重なり」(読みはひらがな，品詞は noun か properNoun，分野は tools/term_fields.py の id)．
重なりは読みが通常の辞書の語とどう重なるか: 0 は重ならない，1 は同じ読みの語がある(「しかん」の 士官)，
2 は通常の辞書の 2 つの語の読みに分けられる(「たたいた」は「たたい」と「た」)．Hajime IME は重なる語の点数を下げ，
文の中でふだんの語を押しのけたり，語の切れ目をまたいで入り込んだり(「ぽんとたたいた」が「ぽんと多対多」)しないようにする．
行全体の UTF-8 のバイト順に並べる(Hajime IME は読みで二分探索して引く)．同じ語が複数の分野にあれば分野ごとに 1 行にする．

- 通常の辞書(worddict.tsv)に同じ読みと語があれば入れない．通常の辞書の語は，専門用語の辞書を切っても出るようにするため
- 通常の辞書に同じ読みで書き方の似た語があれば入れない．似ているとは，字の並びの似方が VARIANT_SIMILARITY 以上(「聖観音」に対する「正観音」)か，
  片方の漢字がすべてもう片方に含まれる(「寄り切り」に対する「寄りきり」，「あいまい検索」に対する「曖昧検索」)こと．
  書き方の違いは点数を下げても Zenzai が選んでしまい，ふだんの書き方を押しのけるため．字の重ならない同音の語(「士官」に対する「篩管」)は入れる
- JMdict: 分野の印(<field>)が付いた語義で，品詞が名詞のもの(名詞・名詞的に使う形容動詞と「の」形容詞)．
  古語・廃語の語義と，不規則・古い・まれ・探すときだけの表記と読みは除く．ひらがなだけの語は変換しても変わらないので除く
- カタカナだけの語(「オンチョム」)は入れない．カタカナへの変換でいつも候補に出るうえ，辞書にあると点数を下げても Zenzai の選び方が変わり，
  ほかの語の切れ目まで変えてしまう(「テンペとオンチョム」が「テンペトオンチョム」)ため
- Wikidata: tools/fetch_wikidata_terms.py が取った一覧(sources/wikidata-terms.tsv)
- 語の全角の英数字と記号(JMdict の「ＪＩＴコンパイラー」)は半角にする(通常の辞書の書き方に合わせる)
- 読みはひらがなと長音だけで，MIN_READING(3)文字から DefaultSettings.maximumImportedReadingLength(32)文字まで，語は maximumImportedWordLength(64)文字まで．
  短い読みの専門用語(「きり」→ 限り)は，ふだんの語の変換に割り込みやすいので入れない
"""
import difflib
import json
import pathlib
import re
import sys
import tarfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from term_fields import BY_JMDICT, FIELDS  # noqa: E402

NOUN_POS = {"n", "n-pr", "n-pref", "n-suf", "n-adv", "n-t", "adj-no", "adj-na"}
EXCLUDED_MISC = {"arch", "obs"}
EXCLUDED_KANJI = {"iK", "oK", "rK", "sK"}
EXCLUDED_KANA = {"ik", "ok", "sk"}
PROPER_FIELDS = {"tradem"}
MIN_READING = 3
VARIANT_SIMILARITY = 0.5
MAX_READING = 32
MAX_WORD = 64
READING = re.compile(r"^[ぁ-ゔー]+$")
HIRAGANA_WORD = re.compile(r"^[ぁ-ゔー]+$")
KATAKANA_WORD = re.compile(r"^[ァ-ヴー・＝]+$")
TO_HIRAGANA = {c: c - 0x60 for c in range(0x30A1, 0x30F5)}
TO_KATAKANA = {c: c + 0x60 for c in range(0x3041, 0x3095)}
HALF_WIDTH = {c: c - 0xFEE0 for c in range(0xFF01, 0xFF5F)}


def applies(targets, text):
    return targets == ["*"] or text in targets


def jmdict_terms(words):
    """(読み, 語, 品詞, 分野) の並び"""
    for entry in words:
        kanji = [k["text"] for k in entry["kanji"] if not EXCLUDED_KANJI & set(k["tags"])]
        kana = [k for k in entry["kana"] if not EXCLUDED_KANA & set(k["tags"])]
        for sense in entry["sense"]:
            fields = {BY_JMDICT[tag] for tag in sense["field"] if tag in BY_JMDICT}
            if not fields or not NOUN_POS & set(sense["partOfSpeech"]) or EXCLUDED_MISC & set(sense["misc"]):
                continue
            proper = "n-pr" in sense["partOfSpeech"] or PROPER_FIELDS & set(sense["field"])
            word_class = "properNoun" if proper else "noun"
            pairs = []
            for reading in kana:
                if not applies(sense["appliesToKana"], reading["text"]):
                    continue
                for word in kanji:
                    if applies(sense["appliesToKanji"], word) and applies(reading["appliesToKanji"], word):
                        pairs.append((reading["text"], word))
                # 漢字の表記が無い語と，ふつうかなで書く語は，かなの表記も語にする
                if not kanji or "uk" in sense["misc"] or not reading["appliesToKanji"]:
                    pairs.append((reading["text"], reading["text"]))
            for reading, word in pairs:
                for field in sorted(fields):
                    yield reading.translate(TO_HIRAGANA), word, word_class, field


def wikidata_terms(path):
    proper = {f.id for f in FIELDS if f.proper}
    for line in path.read_text(encoding="utf-8").splitlines():
        reading, word, field, _ = line.split("\t")
        yield reading, word, "properNoun" if field in proper else "noun", field


def kanji(word):
    return {c for c in word if "\u4e00" <= c <= "\u9fff" or c in "々〆ヶ"}


def is_variant(word, other):
    """同じ読みの 2 つの語が，書き方の違いか"""
    if difflib.SequenceMatcher(None, word, other).ratio() >= VARIANT_SIMILARITY:
        return True
    mine, theirs = kanji(word), kanji(other)
    return bool(mine & theirs) and (mine <= theirs or theirs <= mine)


def valid(reading, word):
    return (READING.match(reading) and MIN_READING <= len(reading) <= MAX_READING and 0 < len(word) <= MAX_WORD
            and not HIRAGANA_WORD.match(word) and not KATAKANA_WORD.match(word) and not any(c.isspace() for c in word))


def main():
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    worddict, jmdict, wikidata, output = (pathlib.Path(arg) for arg in sys.argv[1:])
    # 読み(カタカナ)ごとの通常の辞書の語
    words_by_reading = {}
    with worddict.open(encoding="utf-8") as file:
        for line in file:
            columns = line.split("\t", 2)
            words_by_reading.setdefault(columns[0], []).append(columns[1])
    with tarfile.open(jmdict) as archive:
        member = next(m for m in archive.getmembers() if m.name.endswith(".json"))
        words = json.load(archive.extractfile(member))["words"]
    rows = {}
    skipped = 0
    variants = 0
    for reading, word, word_class, field in [*jmdict_terms(words), *wikidata_terms(wikidata)]:
        word = word.translate(HALF_WIDTH)
        if not valid(reading, word):
            continue
        same_reading = words_by_reading.get(reading.translate(TO_KATAKANA), [])
        if word in same_reading:
            skipped += 1
            continue
        if any(is_variant(word, other) for other in same_reading):
            variants += 1
            continue
        # 同じ読みと語と分野が両方の元にあれば，固有名詞より名詞を優先する(JMdict の品詞の方が確か)
        key = (reading, word, field)
        if key not in rows or word_class == "noun":
            rows[key] = word_class
    def overlap(reading):
        katakana = reading.translate(TO_KATAKANA)
        if katakana in words_by_reading:
            return "1"
        if any(katakana[:i] in words_by_reading and katakana[i:] in words_by_reading for i in range(1, len(katakana))):
            return "2"
        return "0"

    lines = sorted((f"{r}\t{w}\t{c}\t{f}\t{overlap(r)}" for (r, w, f), c in rows.items()), key=lambda line: line.encode())
    output.write_text("".join(line + "\n" for line in lines), encoding="utf-8")
    counts = {}
    for (_, _, field) in rows:
        counts[field] = counts.get(field, 0) + 1
    homophones = sum(1 for line in lines if line.endswith("\t1"))
    splittable = sum(1 for line in lines if line.endswith("\t2"))
    print(f"書きました: {output}({len(lines)} 行．うち同音 {homophones} 行，2 つの語に分けられる {splittable} 行．通常の辞書にあるので除いた {skipped} 件，書き方の違いなので除いた {variants} 件)",
          file=sys.stderr)
    print("，".join(f"{f.id} {counts.get(f.id, 0)}" for f in FIELDS), file=sys.stderr)


if __name__ == "__main__":
    main()
