"""tools/build_terms.py が，分野の付いた語のうち通常の辞書に無い語を，分野と同音の印を付けて並べること"""
import io
import json
import pathlib
import subprocess
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from fixtures import write_worddict  # noqa: E402

TOOL = pathlib.Path(__file__).resolve().parents[1] / "tools" / "build_terms.py"


def entry(kanji, kana, senses):
    """jmdict-simplified の語．kanji は (表記, 印)，kana は (読み, 印, 当てはまる表記)"""
    return {
        "kanji": [{"text": text, "tags": list(tags), "common": False} for text, tags in kanji],
        "kana": [{"text": text, "tags": list(tags), "appliesToKanji": list(applies), "common": False} for text, tags, applies in kana],
        "sense": senses,
    }


def sense(pos=("n",), field=("med",), misc=(), kanji=("*",), kana=("*",)):
    return {"partOfSpeech": list(pos), "field": list(field), "misc": list(misc), "appliesToKanji": list(kanji), "appliesToKana": list(kana)}


class BuildTermsTests(unittest.TestCase):
    def run_tool(self, words, worddict=(), wikidata=""):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            data = json.dumps({"words": words}).encode()
            with tarfile.open(root / "jmdict.json.tgz", "w:gz") as archive:
                info = tarfile.TarInfo("jmdict-eng.json")
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
            write_worddict(root / "worddict.tsv", worddict)
            (root / "wikidata.tsv").write_text(wikidata, encoding="utf-8")
            result = subprocess.run([sys.executable, "-I", str(TOOL), str(root / "worddict.tsv"), str(root / "jmdict.json.tgz"),
                                     str(root / "wikidata.tsv"), str(root / "terms.tsv")], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            return [line.split("\t") for line in (root / "terms.tsv").read_text(encoding="utf-8").splitlines()]

    def test_adds_noun_with_field(self):
        rows = self.run_tool([entry([("心筋梗塞", ())], [("しんきんこうそく", (), ["*"])], [sense()])])
        self.assertEqual(rows, [["しんきんこうそく", "心筋梗塞", "noun", "medicine", "0"]])

    def test_skips_words_in_main_dictionary(self):
        rows = self.run_tool([entry([("心筋梗塞", ())], [("しんきんこうそく", (), ["*"])], [sense()])],
                             worddict=[("シンキンコウソク", "心筋梗塞", 1285, 1285, -9.0)])
        self.assertEqual(rows, [])

    def test_skips_variants_of_main_dictionary_words(self):
        words = [
            entry([("寄りきり", ())], [("よりきり", (), ["*"])], [sense(field=("sumo",))]),
            entry([("曖昧検索", ())], [("あいまいけんさく", (), ["*"])], [sense(field=("comp",))]),
            entry([("正観音", ())], [("しょうかんのん", (), ["*"])], [sense(field=("Buddh",))]),
        ]
        worddict = [("ヨリキリ", "寄り切り", 1285, 1285, -9.0), ("アイマイケンサク", "あいまい検索", 1285, 1285, -9.0),
                    ("ショウカンノン", "聖観音", 1285, 1285, -9.0)]
        self.assertEqual(self.run_tool(words, worddict=worddict), [])

    def test_marks_readings_split_into_two_words(self):
        rows = self.run_tool([entry([("多対多", ())], [("たたいた", (), ["*"])], [sense(field=("comp",))])],
                             worddict=[("タタイ", "叩い", 1285, 1285, -9.0), ("タ", "た", 1285, 1285, -5.0)])
        self.assertEqual(rows, [["たたいた", "多対多", "noun", "computing", "2"]])

    def test_marks_homophones_of_different_words(self):
        rows = self.run_tool([entry([("篩管", ())], [("しかん", (), ["*"])], [sense(field=("bot",))])],
                             worddict=[("シカン", "士官", 1285, 1285, -9.0)])
        self.assertEqual(rows, [["しかん", "篩管", "noun", "biology", "1"]])

    def test_filters_parts_of_speech_and_forms(self):
        words = [
            # 動詞の語義は入れない
            entry([("圧排", ())], [("あっぱい", (), ["*"])], [sense(pos=("v5r",))]),
            # 古語の語義は入れない
            entry([("医薬師", ())], [("いやくし", (), ["*"])], [sense(misc=("arch",))]),
            # まれな表記は入れず，ふつうの表記だけを入れる
            entry([("眼底", ()), ("眼底底", ("rK",))], [("がんてい", (), ["*"])], [sense(field=("anat",))]),
            # ひらがなだけの語とカタカナだけの語は入れない(変換しても変わらないか，カタカナへの変換で出る)
            entry([], [("ぺぷしん", (), [])], [sense(field=("biochem",))]),
            entry([], [("プラステロン", (), [])], [sense(field=("pharm",))]),
            # 英字を含む語は入れる
            entry([], [("ＤＮＡポリメラーゼ", (), [])], [sense(field=("biochem",))]),
            # 読みが短い語は入れない
            entry([("限", ())], [("きり", (), ["*"])], [sense(field=("finc",))]),
        ]
        rows = self.run_tool(words)
        self.assertEqual([(r[0], r[1], r[3]) for r in rows], [("がんてい", "眼底", "medicine")])

    def test_respects_restricted_readings_and_senses(self):
        words = [entry([("胸腺", ()), ("胸線", ())], [("きょうせん", (), ["胸腺"])], [sense(field=("anat",), kanji=("胸腺",))])]
        self.assertEqual([r[1] for r in self.run_tool(words)], ["胸腺"])

    def test_normalizes_full_width_letters_and_keeps_every_field(self):
        words = [entry([("ＪＩＴコンパイラー", ())], [("じっとこんぱいらー", (), ["*"])], [sense(field=("comp",)), sense(field=("engr",))])]
        rows = self.run_tool(words)
        self.assertEqual([(r[1], r[3]) for r in rows], [("JITコンパイラー", "computing"), ("JITコンパイラー", "engineering")])

    def test_merges_wikidata_and_sorts_by_bytes(self):
        wikidata = "ぱいそん\tPython\tcomputing\tQ28865\nかるもなむ\tカルモナム\tchemistry\tQ1\nぎゃくぎょうれつ\t逆行列\tmathematics\tQ2\n"
        rows = self.run_tool([entry([("心筋梗塞", ())], [("しんきんこうそく", (), ["*"])], [sense()])], wikidata=wikidata)
        self.assertEqual([r[0] for r in rows], sorted([r[0] for r in rows], key=lambda reading: reading.encode()))
        self.assertIn(["ぱいそん", "Python", "properNoun", "computing", "0"], rows)
        self.assertIn(["ぎゃくぎょうれつ", "逆行列", "noun", "mathematics", "0"], rows)
        self.assertNotIn("カルモナム", [r[1] for r in rows])


if __name__ == "__main__":
    unittest.main()
