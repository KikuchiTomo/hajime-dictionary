"""tools/add_neologd.py が，既存の語の並びを変えずに NEologd の語を足すこと"""
import lzma
import pathlib
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from fixtures import read_worddict, readings, write_ipadic, write_worddict  # noqa: E402

TOOL = pathlib.Path(__file__).resolve().parents[1] / "tools" / "add_neologd.py"
POS = "名詞,固有名詞,一般,*,*,*"


def row(word, reading, cost, lid=1288):
    return f"{word},{lid},{lid},{cost},{POS},{word},{reading},{reading}\n"


class AddNeologdTests(unittest.TestCase):
    def run_tool(self, worddict, seed):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            (root / "neologd").mkdir()
            with lzma.open(root / "neologd" / "seed.csv.xz", "wt", encoding="utf-8") as file:
                file.write("".join(seed))
            write_ipadic(root / "left-id.def")
            write_worddict(root / "worddict.tsv", worddict)
            result = subprocess.run([sys.executable, "-I", str(TOOL), str(root / "worddict.tsv"), str(root / "neologd"),
                                     str(root / "left-id.def"), str(root / "out.tsv")], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            return read_worddict(root / "out.tsv")

    def setUp(self):
        # 両方の辞書にある語(コスト 1000 → 値 -10，コスト 3000 → 値 -12)で，コストと値の対応を求めさせる
        common = readings(120)
        self.worddict = [(r, f"共{i}", 1288, 1288, -10.0 if i < 60 else -12.0) for i, r in enumerate(common)]
        self.seed = [row(f"共{i}", r, 1000 if i < 60 else 3000) for i, r in enumerate(common)]
        self.worddict.append(("キタヤマダ", "北山田", 1288, 1288, -9.0))

    def test_adds_new_words_with_converted_value(self):
        values = self.run_tool(self.worddict, self.seed + [row("南山台", "ミナミヤマダイ", 2250)])
        # コストの区間の中ほど(1250 と 3250)のあいだのコスト 2250 は -11．まれな語なので 1 下げる
        self.assertAlmostEqual(values[("ミナミヤマダイ", "南山台")], -12.0, places=3)

    def test_places_new_words_below_existing_words_of_same_reading(self):
        values = self.run_tool(self.worddict, self.seed + [row("喜多山田", "キタヤマダ", 0)])
        self.assertLess(values[("キタヤマダ", "喜多山田")], values[("キタヤマダ", "北山田")])

    def test_skips_existing_pairs_and_filtered_words(self):
        values = self.run_tool(self.worddict, self.seed + [row("北山田", "キタヤマダ", 0), row("あかるうううういっ", "アカルーイッ", 0)])
        self.assertAlmostEqual(values[("キタヤマダ", "北山田")], -9.0)
        self.assertNotIn(("アカルーイッ", "あかるうううういっ"), values)

    def test_skips_rows_whose_pos_does_not_match_ipadic(self):
        values = self.run_tool(self.worddict, self.seed + [row("西山台", "ニシヤマダイ", 2000, lid=1285)])
        self.assertNotIn(("ニシヤマダイ", "西山台"), values)


if __name__ == "__main__":
    unittest.main()
