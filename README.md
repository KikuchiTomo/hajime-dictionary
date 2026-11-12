# hajime-dictionary

[Hajime IME](https://github.com/KikuchiTomo/Hajime) のかな漢字変換の辞書です．[azooKey](https://github.com/azooKey/AzooKeyKanaKanjiConverter) の辞書に，[Mozc](https://github.com/google/mozc) の辞書(dictionary_oss)にしかない語と，[Wikidata](https://www.wikidata.org/) から作った外来語の英字の綴り(「レッドハット」→ Red Hat，「にゅーらる」→ neural)を足し，さらに [Mozc UT 辞書](https://github.com/utuhiro78)(SudachiDict・NEologd・人名・地名・Wikipedia の見出し・EDICT2)と，NEologd・SudachiDict の元のデータの語を足しています．v0.4.0 から CC BY-SA 4.0 の語を含むので，辞書は CC BY-SA 4.0 の条件で配布します(「ライセンス」)．azooKey の辞書と同じ形(LOUDS)なので，azooKey のエンジンを使う IME から読めます．

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
| Mozc UT 辞書から足した語 | 1,858,692 |
| NEologd の元のデータから足した語 | 1,398,843 |
| SudachiDict の元のデータから足した名詞 | 57,146 |
| 合計 | 4,719,346 |

展開すると約 279 MB です．

## 作り方

```sh
./build.sh 0.4.0
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
5. `tools/add_ut.py` が，Mozc UT 辞書の語を足します(下の「Mozc UT 辞書の語」)
6. `tools/add_neologd.py` と `tools/add_sudachi.py` が，NEologd と SudachiDict の元のデータの語を足します(下の「NEologd と SudachiDict の元のデータの語」)
7. `tools/demote_sokuon_variants.py` が，促音を落とした読みの揺れの値を下げます(下の「促音を落とした読みの揺れ」)
8. `tools/assemble.sh` が，fork の `DictionaryBuilder` で LOUDS を作ります．接続のコスト・予測・意味の接続は azooKey の辞書のものをそのまま使います

語を足す道具のテストは `python3 -m unittest discover -s tests` で動きます(除く語の決まり・揺れの読み・NEologd と SudachiDict の語の足し方)．

## 外来語の英字の綴り

`sources/wikidata-loanwords.tsv` は，`tools/fetch_wikidata.py` が Wikidata(CC0)から作った「カタカナの読みと英字の綴り」の一覧です．辞書を作るときはこのファイルだけを使い，Wikidata には問い合わせません．作り直すときは次を動かし，差分を確かめてからコミットします．

```sh
python3 -I tools/fetch_wikidata.py sources/wikidata-loanwords.tsv --raw work/wikidata-raw.json
```

- 一覧に残すのは，日本語のラベルか別名がカタカナだけの項目のうち，英語のラベルとカタカナの子音の並びが似ているものです(同じ項目でも名前の違う別の物を除くため)．曖昧さ回避・生物の分類群・論文などの項目は除きます．固有名詞は 15 以上，人は 50 以上の言語版がある項目だけを残します
- 辞書に足すのは，同じ読みのカタカナ語が辞書にあるか，読みが辞書に無い語だけです．かなや漢字の語だけがある読み(「サンサイ」→ 山菜)には足しません
- 打ち方の揺れの読み(ヴ → ブ，トゥ → ツ，末尾の長音を除いたもの)も足します．「ウブンツ」でも Ubuntu が出ます
- 値は，同じ綴りが別の読みで辞書にあればその値に，同じ読みのカタカナ語があればその語の少し下に合わせます．カタカナ語が先に出て，英字はその次に選べます

## Mozc UT 辞書の語

utuhiro78 さんの Mozc UT 辞書のうち，配布物に入れられるライセンスの 6 つ(mozcdic-ut-sudachidict・mozcdic-ut-neologd・mozcdic-ut-personal-names・mozcdic-ut-place-names・mozcdic-ut-jawiki・mozcdic-ut-edict2)から語を足します．`sources/sources.txt` にリポジトリのコミットと SHA-256 を書いてあり，同じファイルから同じ辞書ができます．

UT 辞書は読みと表記だけで品詞を持たず，雑多な語も多いので，次のように足します．

- 品詞: 人名の辞書は「名詞,固有名詞,人名,一般」，地名の辞書は「名詞,固有名詞,地域,一般」，SudachiDict・NEologd・Wikipedia の見出しから作った辞書は「名詞,固有名詞,一般」，EDICT2 から作った辞書は「名詞,一般」にします．EDICT2 は動詞・形容詞・句も含むので，表記がひらがなで終わる語は足しません
- 除く語: 読みが 4 文字より短いか 20 文字より長い語，表記が 20 文字より長い語，名前に使う記号(空白・=-&'.!?)以外の記号やほかの文字体系(ハングル・ギリシャ文字など)を含む語，記号と数字だけの語，表記のかなの部分が読みに現れない語(「四国ドック」を「シコクドックカブシキガイシャ」と読む組など)，英字だけの表記で，英字を 1 文字ずつ読んだ読みでも子音の並びが似た読みでもない語
- 値: 既存の語より控えめにします．品詞ごとに既存の語の値の下から 10% の位置を基準にし，元の辞書のコストと，複数の UT 辞書にあるかで少しだけ上げます．同じ読みの語が既にあれば，そのどれよりも下に置きます．既存の候補の並びは変わらず，UT 辞書の語はそのあとに入ります

GPL の UT 辞書(mozcdic-ut-skk-jisyo・mozcdic-ut-alt-cannadic)は使いません．UT 辞書を組み合わせる merge-ut-dictionaries が使う Wikipedia の見出し(CC BY-SA)によるコストの調整も使いません．

## NEologd と SudachiDict の元のデータの語

Mozc UT 辞書の NEologd・SudachiDict は名詞だけなので，元のデータからも語を足します(v0.4.0 から)．どちらも Apache License 2.0 です．

- [mecab-ipadic-NEologd](https://github.com/neologd/mecab-ipadic-neologd) の seed(固有名詞・一般名詞・形容詞・副詞・表記の揺れ)を `tools/add_neologd.py` で足します．品詞は IPAdic の番号なので，そのまま使います．形容詞を伸ばした書き方(「あかるうううういっ」)や顔文字など，表記のかなが読みに現れない語や記号を含む語は，Mozc UT 辞書と同じ決まり(`tools/wordfilter.py`)で除きます
- [SudachiDict](https://github.com/WorksApplications/SudachiDict) の small・core・notcore の名詞を `tools/add_sudachi.py` で足します．品詞の体系が違うので，名詞の小分類を IPAdic の品詞に引き直します(動詞・形容詞は活用の型の対応が要るので足しません)
- 値: 両方の辞書にある同じ品詞の語で，元の辞書のコストと azooKey の値の対応を求め(Mozc の語と同じ)，まれな語が多いので 1 下げます．同じ読みの語が既にあれば，そのどれよりも下に置きます．既存の候補の並びは変わりません

## 促音を落とした読みの揺れ

azooKey と Mozc の辞書には，促音を落として打ったときのための読みの揺れ(決して の「けして」，支える の「つかえる」，湿気 の「しけ」)が入っています．揺れの読みが，同じ読みのふつうの語(けして の「消して」，しけ の「時化」)より先に出ないよう，`tools/demote_sokuon_variants.py` で値を下げます．

- 同じ表記に，読み R と，R に「ッ」を 1 つ足した読み R' があり，R' のほうがよく使われる(値が大きい)とき，R を揺れとみなして値を 5 下げます．語は消さないので，候補から選べ，Zenzai が文脈から選ぶこともできます(「けしてゆるさない」は「決して許さない」)
- 下げた語と同じ読み・同じ品詞で，表記が読みのかなそのものの語(決して に対する副詞の「けして」)も一緒に下げます
- R のほうがよく使われる組(欲し の「ほし」と「ほっし」)は変えません．かなの表記の語どうし(バタ と バッタ)は別の語のことが多いので，組にしません

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

v0.3.0(Mozc UT 辞書の語を足した版)と v0.2.0 の比較です(第 1 候補の正解率 / 上位 10 候補に正解が入った割合)．

| 評価セット | v0.2.0，Zenzai あり | v0.3.0，Zenzai あり | v0.2.0，Zenzai なし | v0.3.0，Zenzai なし |
|---|---|---|---|---|
| 人名(Wikidata，300 語) | 28.7% / 44.0% | 28.7% / 89.7% | 27.3% / 45.3% | 28.3% / 65.0% |
| 地名(Wikidata，300 語) | 43.3% / 58.3% | 43.3% / 65.0% | 40.3% / 57.7% | 40.3% / 60.3% |
| その他(Wikidata，300 語) | 36.0% / 62.7% | 36.7% / 77.0% | 40.7% / 60.3% | 40.7% / 65.3% |
| AJIMEE-Bench(200 文) | 86.0% / 87.0% | 86.0% / 87.0% | 45.0% / 72.5% | 45.0% / 72.5% |

AJIMEE-Bench と Hajime の文の評価(conversion-basic)・打ち間違いの補正の評価は，1 件ずつ見ても v0.2.0 と同じ結果でした．UT 辞書の語は既存の候補のあとに入るので，第 1 候補はほとんど変わらず，上位 10 候補に入る固有名詞が増えます(Zenzai ありで「ないきむら」の内記村，「きりしまさーびすえりあ」の霧島サービスエリアが 5 番目の候補)．

v0.4.0(Wikipedia の見出し・EDICT2・NEologd と SudachiDict の元のデータの語を足し，促音を落とした読みの揺れを下げた版)と v0.3.0 の比較です(Zenzai small，第 1 候補の正解率 / 上位 10 候補に正解が入った割合)．

| 評価セット | v0.3.0 | v0.4.0 |
|---|---|---|
| 人名(Wikidata，300 語) | 28.7% / 89.7% | 28.7% / 97.0% |
| 地名(Wikidata，300 語) | 43.3% / 65.0% | 43.7% / 76.3% |
| その他(Wikidata，300 語) | 36.7% / 77.0% | 36.7% / 79.0% |
| AJIMEE-Bench(200 文) | 86.0% / 87.0% | 86.0% / 87.0% |
| Tatoeba(人が付けたふりがなの文 1,959 文) | 77.3% / 81.5% | 77.3% / 81.5% |

文の評価(AJIMEE-Bench・Tatoeba・Hajime の conversion-basic と conversion-everyday)は，Zenzai small と xsmall のどちらでも 1 件ずつ見て v0.3.0 と同じでした．文の第 1 候補は Zenzai が決めるので，語を足して上がるのは上位の候補に正しい語が入る割合です．「けして」は，Zenzai を使わない変換で「決して」より「消して」が先に出るようになりました．

## ライセンス

辞書のデータは，元のデータのライセンスに従います．v0.4.0 から Wikipedia の見出し(mozcdic-ut-jawiki)と EDICT2(mozcdic-ut-edict2)の CC BY-SA 4.0 の語を含むので，辞書の全体を CC BY-SA 4.0 の条件で配布します(表示: [NOTICE.md](NOTICE.md)，全文: `LICENSES/CC-BY-SA-4.0.txt`)．ほかの元のデータの条件も [NOTICE.md](NOTICE.md) と `LICENSES/` を見てください．このリポジトリのスクリプトは MIT License です([LICENSE](LICENSE))．
