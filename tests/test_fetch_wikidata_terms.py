"""tools/fetch_wikidata_terms.py が，Wikidata の項目の名前から読みを決め，分野ごとに並べること(問い合わせはしない)"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
from fetch_wikidata_terms import reading_of, terms  # noqa: E402
from term_fields import FIELDS  # noqa: E402


class FetchWikidataTermsTests(unittest.TestCase):
    def test_reading_from_kana_name(self):
        self.assertEqual(reading_of("心筋梗塞", "シンキン・コウソク"), "しんきんこうそく")
        self.assertEqual(reading_of("ActiveBasic", "アクティブ ベーシック"), "あくてぃぶべーしっく")

    def test_reading_from_katakana_label(self):
        self.assertEqual(reading_of("フーリエ・ヘンカン", None), "ふーりえへんかん")

    def test_no_reading(self):
        self.assertIsNone(reading_of("心筋梗塞", None))
        self.assertIsNone(reading_of("RNA", "RNA"))

    def test_terms_by_field(self):
        field = next(f for f in FIELDS if f.id == "medicine")
        cls = field.wikidata[0]
        results = {cls: [["Q1", "心筋梗塞", "しんきんこうそく"], ["Q1", "心筋梗塞", "しんきんこうそく"], ["Q2", "痛み", None]]}
        self.assertEqual(list(terms(results)), [("しんきんこうそく", "心筋梗塞", "medicine", "Q1")])


if __name__ == "__main__":
    unittest.main()
