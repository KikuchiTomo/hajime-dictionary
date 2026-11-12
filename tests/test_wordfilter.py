"""tools/wordfilter.py の除く語の決まり"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
from wordfilter import problem  # noqa: E402


class ProblemTests(unittest.TestCase):
    def test_accepts_ordinary_words(self):
        for reading, word in [("トウキョウト", "東京都"), ("サクラザキ", "桜崎"), ("アカルイ", "明るい"), ("マツケサキ", "松ケ崎")]:
            with self.subTest(word=word):
                self.assertIsNone(problem(reading, word))

    def test_rejects_short_and_long_readings(self):
        self.assertEqual(problem("トウ", "塔"), "読みが短い")
        self.assertEqual(problem("ア" * 21, "亜" * 3), "読みが長い")

    def test_rejects_elongated_spellings_whose_kana_do_not_match(self):
        # NEologd の形容詞の展開形の「伸ばした書き方」は，表記のかなが読みに現れない
        self.assertEqual(problem("アカルーイッ", "あかるうううういっ"), "表記のかなが読みと合わない")

    def test_rejects_symbols_and_other_scripts(self):
        self.assertEqual(problem("カオモジ", "(´ﾟЗﾟ｀)"), "表記に使えない文字")
        self.assertEqual(problem("アンニョン", "안녕"), "表記に使えない文字")

    def test_rejects_digits_only(self):
        self.assertEqual(problem("ニセンニジュウ", "2020"), "表記が記号と数字だけ")

    def test_latin_words_must_match_reading(self):
        self.assertIsNone(problem("ユーエスビー", "USB"))
        self.assertEqual(problem("サムライフィクション", "sf"), "英字の表記が読みと合わない")


if __name__ == "__main__":
    unittest.main()
