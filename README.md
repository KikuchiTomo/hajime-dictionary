# hajime-dictionary

[Hajime IME](https://github.com/KikuchiTomo/Hajime) のかな漢字変換の辞書です．[azooKey](https://github.com/azooKey/AzooKeyKanaKanjiConverter) の辞書に，[Mozc](https://github.com/google/mozc) の辞書(dictionary_oss)にしかない語と，[Wikidata](https://www.wikidata.org/) から作った外来語の英字の綴り(「レッドハット」→ Red Hat，「にゅーらる」→ neural)を足しています．azooKey の辞書と同じ形(LOUDS)なので，azooKey のエンジンを使う IME から読めます．

## 入手

[Releases](https://github.com/KikuchiTomo/hajime-dictionary/releases) から `hajime-dictionary-<版>.tar.gz` を取得してください．SHA-256 は同じ場所の `.sha256` にあります．展開した `Dictionary/` を，azooKey のエンジンに辞書のディレクトリとして渡します．

```swift
let converter = KanaKanjiConverter(dicdataStore: DicdataStore(dictionaryURL: dictionaryDirectory))
```

`Dictionary/SHA256SUMS` に辞書のファイルごとの SHA-256 があります．使う側で一覧の SHA-256 を持っておき，一覧と各ファイルを確かめてから読むと，差し替えられた辞書を読まずに済みます．

辞書の形は AzooKeyKanaKanjiConverter の版に合わせています．作るときに使った版は `builder/Package.swift` の revision です．

## 中身

| | 語の数 |
|---|---|
| azooKey の辞書の語 | 566,214 |
| Mozc から足した語 | 707,915 |
| Wikidata から足した外来語の英字の綴り | 130,536 |
| 合計 | 1,404,665 |

展開すると約 78 MB です．

## 作り方

```sh
./build.sh 0.2.0
```

Swift 6.1 以降と Python 3 が要ります．Python のスクリプトは標準ライブラリだけで動きます．

1. `tools/fetch_sources.sh` が，`sources/sources.txt` に書いた元のデータを取得し，SHA-256(azooKey の辞書は git のコミット)を確かめます
2. `tools/dump_azookey.py` が，azooKey の辞書の語をすべて TSV に書き出します
3. `tools/merge_mozc.py` が，Mozc にしかない語を足します
   - 品詞: azooKey の品詞の番号は IPAdic の left-id と同じです．Mozc の id.def の品詞の文字列を，IPAdic の番号に引き直します．活用の行が決まっていない品詞(「五段動詞」など)の語は，正しく対応しないので足しません
   - コスト: 両方の辞書にある同じ品詞の語から，Mozc のコストの区間ごとに azooKey の値の中央値を求め，その間を線形に補って換算します
   - 読みが 4 文字より短い語は足しません．短い読みでは，まれな語が既存の語を押しのけて変換を悪くしたためです(「じたい」が「次隊」になるなど)
   - 読みをわざと誤らせた表記ゆれの補正の行(SPELLING_CORRECTION)は足しません
4. `tools/add_loanwords.py` が，外来語の英字の綴りを足します(下の「外来語の英字の綴り」)
5. `tools/assemble.sh` が，fork の `DictionaryBuilder` で LOUDS を作ります．接続のコスト・予測・意味の接続は azooKey の辞書のものをそのまま使います

## 外来語の英字の綴り

`sources/wikidata-loanwords.tsv` は，`tools/fetch_wikidata.py` が Wikidata(CC0)から作った「カタカナの読みと英字の綴り」の一覧です．辞書を作るときはこのファイルだけを使い，Wikidata には問い合わせません．作り直すときは次を動かし，差分を確かめてからコミットします．

```sh
python3 -I tools/fetch_wikidata.py sources/wikidata-loanwords.tsv --raw work/wikidata-raw.json
```

- 一覧に残すのは，日本語のラベルか別名がカタカナだけの項目のうち，英語のラベルとカタカナの子音の並びが似ているものです(同じ項目でも名前の違う別の物を除くため)．曖昧さ回避・生物の分類群・論文などの項目は除きます．固有名詞は 15 以上，人は 50 以上の言語版がある項目だけを残します
- 辞書に足すのは，同じ読みのカタカナ語が辞書にあるか，読みが辞書に無い語だけです．かなや漢字の語だけがある読み(「サンサイ」→ 山菜)には足しません
- 打ち方の揺れの読み(ヴ → ブ，トゥ → ツ，末尾の長音を除いたもの)も足します．「ウブンツ」でも Ubuntu が出ます
- 値は，同じ綴りが別の読みで辞書にあればその値に，同じ読みのカタカナ語があればその語の少し下に合わせます．カタカナ語が先に出て，英字はその次に選べます

## 評価

Hajime の `make evaluate DICTIONARY=<展開した Dictionary>` で測れます．v0.1.0 の結果(Zenzai なし，第 1 候補の正解率 / 上位 10 候補に正解が入った割合)は次のとおりです．

| 評価セット | azooKey の辞書 | この辞書 |
|---|---|---|
| 人名(Wikidata，300 語) | 18.7% / 35.7% | 27.3% / 45.3% |
| 地名(Wikidata，300 語) | 30.7% / 49.3% | 41.0% / 58.3% |
| その他(Wikidata，300 語) | 34.0% / 55.0% | 40.7% / 60.7% |
| AJIMEE-Bench(200 文) | 43.5% | 45.0% |

Zenzai を使う場合，第 1 候補は変わらず，上位 10 候補に正解が入る割合が 8〜11 ポイント上がりました．

v0.2.0(外来語の英字の綴りを足した版)は，Zenzai を使う場合も使わない場合も，上の評価セットの結果が v0.1.1 と同じでした．英字の綴りはカタカナ語の次の候補に入ります．Zenzai を使う場合，「うぶんつ」の Ubuntu・「れっどはっと」の Red Hat は 2 番目，「にゅーらる」の neural は 3 番目の候補です(v0.1.1 では上位 10 候補に入りません)．

## ライセンス

辞書のデータは，元のデータのライセンスに従います．[NOTICE.md](NOTICE.md) と `LICENSES/` を見てください．このリポジトリのスクリプトは MIT License です([LICENSE](LICENSE))．
