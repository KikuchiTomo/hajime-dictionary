"""tools/demote_sokuon_variants.py が，促音を落とした読みの揺れだけを下げること"""
import pathlib
import subprocess
import sys
import tempfile
import unittest

TOOL = pathlib.Path(__file__).resolve().parents[1] / "tools" / "demote_sokuon_variants.py"
ROWS = [
    # 読み 表記 左 右 意味 値
    ("ケシテ", "決して", 1281, 1281, 268, -8.80),
    ("ケッシテ", "決して", 1281, 1281, 268, -8.17),
    ("ケシテ", "けして", 1281, 1281, 247, -10.85),
    ("ケッシテ", "けっして", 1281, 1281, 247, -10.81),
    ("ケシテ", "消して", 735, 307, 17, -10.14),
    # ッのない読みのほうがよく使われる組は変えない
    ("ホシ", "欲し", 100, 100, 1, -4.37),
    ("ホッシ", "欲し", 100, 100, 1, -8.70),
    # かなの表記の語どうしは別の語なので組にしない
    ("バタ", "バタ", 1285, 1285, 501, -10.0),
    ("バッタ", "バッタ", 1285, 1285, 501, -9.0),
]


def run(rows):
    with tempfile.TemporaryDirectory() as directory:
        source, destination = pathlib.Path(directory, "in.tsv"), pathlib.Path(directory, "out.tsv")
        source.write_text("".join(f"{r}\t{w}\t{l}\t{c}\t{m}\t{v:.4f}\n" for r, w, l, c, m, v in rows), encoding="utf-8")
        subprocess.run([sys.executable, "-I", str(TOOL), str(source), str(destination)], check=True, capture_output=True)
        return {(c[0], c[1]): float(c[5]) for c in (line.split("\t") for line in destination.read_text(encoding="utf-8").splitlines())}


class DemoteTests(unittest.TestCase):
    def test_demotes_sokuon_dropped_reading_and_its_kana_spelling(self):
        values = run(ROWS)
        self.assertAlmostEqual(values[("ケシテ", "決して")], -13.80)
        self.assertAlmostEqual(values[("ケシテ", "けして")], -15.85)

    def test_keeps_standard_readings_and_other_words(self):
        values = run(ROWS)
        self.assertAlmostEqual(values[("ケッシテ", "決して")], -8.17)
        self.assertAlmostEqual(values[("ケシテ", "消して")], -10.14)
        self.assertAlmostEqual(values[("ホシ", "欲し")], -4.37)
        self.assertAlmostEqual(values[("バタ", "バタ")], -10.0)

    def test_variant_falls_below_ordinary_word_of_same_reading(self):
        values = run(ROWS)
        self.assertLess(values[("ケシテ", "決して")], values[("ケシテ", "消して")])


if __name__ == "__main__":
    unittest.main()
