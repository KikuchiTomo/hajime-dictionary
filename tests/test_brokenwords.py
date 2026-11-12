"""tools/brokenwords.py の壊れた書き方の決まり"""
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from brokenwords import (  # noqa: E402
    OkuriganaNouns, SameReadingWords, dropped_okurigana, azookey_fragment, azookey_mixed_spelling, broken, load_joyo,
)
from fixtures import write_unihan  # noqa: E402


class BrokenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "Unihan.zip"
            write_unihan(path)
            cls.joyo = load_joyo(path)
        cls.same = SameReadingWords()
        for reading, word, value in [("ハッセイ", "発生", -7.5), ("ハッセイ", "発声", -11.4), ("アッセイ", "圧制", -14.0),
                                     ("ヒッコシ", "引越", -12.0), ("フッソ", "弗素", -15.0), ("ギンザケ", "銀鮭", -14.8),
                                     ("ハッチュウ", "発注", -9.9)]:
            cls.same.add(reading, word, value, "名詞,一般,*,*,*,*,*")
        # 同じ読みの動詞(青ざめる)とは比べない
        cls.same.add("アオザメ", "青ざめ", -12.1, "動詞,自立,*,*,一段,連用形,*")

    def check(self, reading, word, value=-17.0, **options):
        return broken(reading, word, value, self.same, self.joyo, **options)

    def test_rejects_mixed_spellings_split_at_sokuon(self):
        self.assertEqual(self.check("ハッセイ", "はっ声"), "促音で切った交ぜ書き")
        self.assertEqual(self.check("ハッセイ", "ハッ生"), "促音で切った交ぜ書き")
        self.assertEqual(self.check("アッセイ", "アッ制"), "促音で切った交ぜ書き")
        self.assertEqual(self.check("ハッチュウ", "はっ注"), "促音で切った交ぜ書き")

    def test_keeps_okurigana_sokuon_and_non_joyo_kana(self):
        # 送りがなの促音は元の語の漢字の位置に当たらない
        self.assertIsNone(self.check("ヒッコシ", "引っ越し"))
        # 常用漢字でない字(弗)をかなにした書き方は残す
        self.assertIsNone(self.check("フッソ", "ふっ素"))

    def test_rejects_kana_spelling_of_much_more_common_kanji_word(self):
        self.assertEqual(self.check("ハッセイ", "はっせい"), "読みのかなだけ")
        self.assertEqual(self.check("ハッセイ", "ハッセイ"), "読みのかなだけ")

    def test_keeps_katakana_names_of_living_things(self):
        # カタカナが習わしの語は，漢字の語と値がほとんど変わらない
        self.assertIsNone(self.check("ギンザケ", "ギンザケ", value=-16.3))
        self.assertIsNone(self.check("アオザメ", "アオザメ", value=-16.4))

    def test_keeps_names_and_non_nouns(self):
        self.assertIsNone(self.check("ハッセイ", "ハッセイ", name=True))
        self.assertIsNone(self.check("ハッセイ", "はっせい", noun=False))

    def test_rejects_sokuon_fragments(self):
        self.assertEqual(self.check("ッチュネン", "っちゅねん!"), "読みが促音で始まる")
        self.assertEqual(self.check("ジュウイッ", "十一"), "数詞の促音の読み")
        self.assertIsNone(self.check("ハッポン", "八本"))


class AzooKeyFragmentTests(unittest.TestCase):
    def test_removes_sokuon_fragments_of_azookey(self):
        # 「は」「ッ」「制」とつながって「はッ制」を作る名詞と，「はっ再」を作るかなの数詞
        self.assertEqual(azookey_fragment("ッ", "ッ", "名詞,固有名詞,組織,*,*,*,*"), "読みが促音で始まるカタカナの名詞")
        self.assertEqual(azookey_fragment("ック", "ック", "名詞,一般,*,*,*,*,*"), "読みが促音で始まるカタカナの名詞")
        self.assertEqual(azookey_fragment("ハッ", "はっ", "名詞,数,*,*,*,*,*"), "かなで書いた数詞の促音の読み")
        # 「イッ」「所」とつながって「イッ所に」を作る
        self.assertEqual(azookey_fragment("イッ", "イッ", "名詞,一般,*,*,*,*,*"), "促音で終わる 2 文字のカタカナの名詞")

    def test_keeps_numerals_suffixes_and_other_parts_of_speech(self):
        # 八本 の「ハッ」，江戸っ子 の「っ子」，「っ」で終わる動詞
        self.assertIsNone(azookey_fragment("ハッ", "八", "名詞,数,*,*,*,*,*"))
        self.assertIsNone(azookey_fragment("ハッ", "8", "名詞,数,*,*,*,*,*"))
        self.assertIsNone(azookey_fragment("ッコ", "っ子", "名詞,接尾,一般,*,*,*,*"))
        self.assertIsNone(azookey_fragment("ッ", "っ", "動詞,非自立,*,*,五段・ラ行,連用タ接続,*"))
        self.assertIsNone(azookey_fragment("ハッ", "ハッ", "副詞,助詞類接続,*,*,*,*,*"))
        self.assertIsNone(azookey_fragment("イラッ", "イラッ", "名詞,一般,*,*,*,*,*"))


class AzooKeyMixedSpellingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "Unihan.zip"
            write_unihan(path, joyo="発声生制圧滞注引越素徹底厄介血鬱勃")
            cls.joyo = load_joyo(path)
        cls.words = SameReadingWords()
        for reading, word in [("テッテイ", "徹底"), ("ヤッカイ", "厄介"), ("ウッケツ", "鬱血"), ("ボッパツ", "勃発")]:
            cls.words.add(reading, word, -10.0, "名詞,一般,*,*,*,*,*")

    def check(self, reading, word):
        return azookey_mixed_spelling(reading, word, "名詞,一般,*,*,*,*,*", self.words, self.joyo)

    def test_removes_mixed_spellings_of_joyo_kanji(self):
        self.assertEqual(self.check("テッテイ", "てっ底"), "促音で切った交ぜ書きの名詞")
        self.assertEqual(self.check("ヤッカイ", "やっ介"), "促音で切った交ぜ書きの名詞")

    def test_keeps_newspaper_mixed_spellings(self):
        # 鬱・勃 を常用漢字に含めても，新聞の交ぜ書きとして残す
        self.assertIsNone(self.check("ウッケツ", "うっ血"))
        self.assertIsNone(self.check("ボッパツ", "ぼっ発"))


class AzooKeyDroppedOkuriganaTests(unittest.TestCase):
    NOUN = "名詞,一般,*,*,*,*,*"
    VERB = "動詞,自立,*,*,五段・タ行,連用形,*"

    @classmethod
    def setUpClass(cls):
        cls.words = OkuriganaNouns()
        NOUN, VERB = cls.NOUN, cls.VERB
        # azooKey の辞書の値に近い組(待ち・書き は送りがなを付けた名詞のほうがよく使われる．光り・組み は まれ)
        for reading, word, value, feature in [
            ("マチ", "待ち", -8.94, "名詞,接尾,一般,*,*,*,*"), ("マチ", "待ち", -5.50, VERB), ("カキ", "書き", -9.75, "名詞,接尾,一般,*,*,*,*"),
            ("カキ", "書き", -4.76, VERB), ("ヒカリ", "光り", -18.67, NOUN), ("ヒカリ", "光り", -9.0, VERB), ("クミ", "組み", -11.60, NOUN),
            ("クミ", "組み", -8.0, VERB), ("オビ", "帯び", -9.0, VERB), ("ズミ", "済み", -8.33, "名詞,接尾,一般,*,*,*,*"), ("ズミ", "済み", -7.0, VERB),
            ("カンガエ", "考え", -8.71, NOUN), ("カンガエ", "考え", -6.0, "動詞,自立,*,*,一段,連用形,*"),
        ]:
            cls.words.add(reading, word, value, feature)

    def check(self, reading, word, value, feature=None):
        return dropped_okurigana(reading, word, value, feature or self.NOUN, self.words)

    def test_removes_single_kanji_nouns_without_usual_okurigana(self):
        self.assertEqual(self.check("マチ", "待", -12.22), "送りがなを落とした 1 字の名詞")
        self.assertEqual(self.check("カキ", "書", -12.19), "送りがなを落とした 1 字の名詞")
        self.assertEqual(self.check("カンガエ", "考", -17.26), "送りがなを落とした 1 字の名詞")

    def test_keeps_nouns_written_without_okurigana(self):
        # 送り仮名の付け方の通則 2 の例外(光・組・帯)，送りがなを付けた名詞がまれなもの，送りがなを付けた名詞が無いもの
        self.assertIsNone(self.check("ヒカリ", "光", -8.91))
        self.assertIsNone(self.check("クミ", "組", -11.69))
        self.assertIsNone(self.check("オビ", "帯", -10.0))
        self.assertIsNone(self.check("マチ", "待", -9.5))

    def test_keeps_compound_readings_suffixes_and_other_parts_of_speech(self):
        # 濁った頭の読み(確認済)，接尾・助数詞の品詞，連用形でない読み
        self.assertIsNone(self.check("ズミ", "済", -13.32))
        self.assertIsNone(self.check("カキ", "書", -16.23, "名詞,接尾,一般,*,*,*,*"))
        self.assertIsNone(self.check("マツ", "待", -20.0))


if __name__ == "__main__":
    unittest.main()
