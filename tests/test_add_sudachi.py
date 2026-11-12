"""tools/add_sudachi.py が，SudachiDict の名詞を IPAdic の品詞に引き直して足すこと"""
import pathlib
import subprocess
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from fixtures import read_worddict, readings, write_ipadic, write_worddict  # noqa: E402

TOOL = pathlib.Path(__file__).resolve().parents[1] / "tools" / "add_sudachi.py"
HEADER = "IndexForm,LeftId,RightId,Cost,Headword,POS1,POS2,POS3,POS4,POS5,POS6,ReadingForm,NormalizedForm\n"


def row(word, reading, cost, pos="名詞,普通名詞,一般,*,*,*", left="5000"):
    return f"{word},{left},{left},{cost},{word},{pos},{reading},{word}\n"


class AddSudachiTests(unittest.TestCase):
    def run_tool(self, worddict, lexicon):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            (root / "sudachi").mkdir()
            for index, name in enumerate(["small_lex", "core_lex", "notcore_lex"]):
                with zipfile.ZipFile(root / "sudachi" / f"{name}.zip", "w") as archive:
                    archive.writestr(f"{name}.csv", HEADER + "".join(lexicon if index == 0 else []))
            write_ipadic(root / "left-id.def")
            write_worddict(root / "worddict.tsv", worddict)
            result = subprocess.run([sys.executable, "-I", str(TOOL), str(root / "worddict.tsv"), str(root / "sudachi"),
                                     str(root / "left-id.def"), str(root / "out.tsv")], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            return read_worddict(root / "out.tsv"), (root / "out.tsv").read_text(encoding="utf-8")

    def setUp(self):
        common = readings(120)
        self.worddict = [(r, f"共{i}", 1285, 1285, -10.0 if i < 60 else -12.0) for i, r in enumerate(common)]
        self.lexicon = [row(f"共{i}", r, 3500 if i < 60 else 5500) for i, r in enumerate(common)]

    def test_adds_common_nouns_as_ipadic_general_nouns(self):
        values, text = self.run_tool(self.worddict, self.lexicon + [row("山小屋群", "ヤマゴヤグン", 4500)])
        self.assertAlmostEqual(values[("ヤマゴヤグン", "山小屋群")], -12.0, places=3)
        self.assertIn("ヤマゴヤグン\t山小屋群\t1285\t1285\t", text)

    def test_maps_proper_noun_subclasses(self):
        _, text = self.run_tool(self.worddict, self.lexicon + [row("北山田", "キタヤマダ", 4500, pos="名詞,固有名詞,地名,一般,*,*")])
        self.assertIn("キタヤマダ\t北山田\t1293\t1293\t", text)

    def test_skips_verbs_and_reference_rows(self):
        values, _ = self.run_tool(self.worddict, self.lexicon + [
            row("走りまわる", "ハシリマワル", 4500, pos="動詞,一般,*,*,五段-ラ行,終止形-一般"),
            row("南山台", "ミナミヤマダイ", 4500, left="-1"),
        ])
        self.assertNotIn(("ハシリマワル", "走りまわる"), values)
        self.assertNotIn(("ミナミヤマダイ", "南山台"), values)


if __name__ == "__main__":
    unittest.main()
