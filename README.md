# hajime-dictionary

[Hajime IME](https://github.com/KikuchiTomo/Hajime) のかな漢字変換の辞書です．[azooKey](https://github.com/azooKey/AzooKeyKanaKanjiConverter) の辞書に，[Mozc](https://github.com/google/mozc) の辞書(dictionary_oss)にしかない語を足しています．azooKey の辞書と同じ形(LOUDS)なので，azooKey のエンジンを使う IME から読めます．

## 入手

[Releases](https://github.com/KikuchiTomo/hajime-dictionary/releases) から `hajime-dictionary-<版>.tar.gz` を取得してください．SHA-256 は同じ場所の `.sha256` にあります．展開した `Dictionary/` を，azooKey のエンジンに辞書のディレクトリとして渡します．

```swift
let converter = KanaKanjiConverter(dicdataStore: DicdataStore(dictionaryURL: dictionaryDirectory))
```

辞書の形は AzooKeyKanaKanjiConverter の版に合わせています．作るときに使った版は `builder/Package.swift` の revision です．

## 中身

| | 語の数 |
|---|---|
| azooKey の辞書の語 | 566,214 |
| Mozc から足した語 | 707,915 |
| 合計 | 1,274,129 |

展開すると約 70 MB です．

## 作り方

```sh
./build.sh 0.1.0
```

Swift 6.1 以降と Python 3 が要ります．Python のスクリプトは標準ライブラリだけで動きます．

1. `tools/fetch_sources.sh` が，`sources/sources.txt` に書いた元のデータを取得し，SHA-256(azooKey の辞書は git のコミット)を確かめます
2. `tools/dump_azookey.py` が，azooKey の辞書の語をすべて TSV に書き出します
3. `tools/merge_mozc.py` が，Mozc にしかない語を足します
   - 品詞: azooKey の品詞の番号は IPAdic の left-id と同じです．Mozc の id.def の品詞の文字列を，IPAdic の番号に引き直します．活用の行が決まっていない品詞(「五段動詞」など)の語は，正しく対応しないので足しません
   - コスト: 両方の辞書にある同じ品詞の語から，Mozc のコストの区間ごとに azooKey の値の中央値を求め，その間を線形に補って換算します
   - 読みが 4 文字より短い語は足しません．短い読みでは，まれな語が既存の語を押しのけて変換を悪くしたためです(「じたい」が「次隊」になるなど)
   - 読みをわざと誤らせた表記ゆれの補正の行(SPELLING_CORRECTION)は足しません
4. `tools/assemble.sh` が，fork の `DictionaryBuilder` で LOUDS を作ります．接続のコスト・予測・意味の接続は azooKey の辞書のものをそのまま使います

## 評価

Hajime の `make evaluate DICTIONARY=<展開した Dictionary>` で測れます．v0.1.0 の結果(Zenzai なし，第 1 候補の正解率 / 上位 10 候補に正解が入った割合)は次のとおりです．

| 評価セット | azooKey の辞書 | この辞書 |
|---|---|---|
| 人名(Wikidata，300 語) | 18.7% / 35.7% | 27.3% / 45.3% |
| 地名(Wikidata，300 語) | 30.7% / 49.3% | 41.0% / 58.3% |
| その他(Wikidata，300 語) | 34.0% / 55.0% | 40.7% / 60.7% |
| AJIMEE-Bench(200 文) | 43.5% | 45.0% |

Zenzai を使う場合，第 1 候補は変わらず，上位 10 候補に正解が入る割合が 8〜11 ポイント上がりました．

## ライセンス

辞書のデータは，元のデータのライセンスに従います．[NOTICE.md](NOTICE.md) と `LICENSES/` を見てください．このリポジトリのスクリプトは MIT License です([LICENSE](LICENSE))．
