# NOTICE

この辞書は，次のデータを組み合わせて作っています．配るときはこのファイルと LICENSES/ を添えてください．

v0.4.0 から，CC BY-SA 4.0 のデータ(Wikipedia の見出しと EDICT2 の語)を含みます．このため辞書の全体は CC BY-SA 4.0 の条件で配布します(全文は LICENSES/CC-BY-SA-4.0.txt)．辞書を作り変えて配るときも，同じ条件で配布してください．

| 元のデータ | 使ったもの | ライセンス | 全文 |
|---|---|---|---|
| [azooKey_dictionary_storage](https://github.com/ensan-hcl/azooKey_dictionary_storage)(コミット 4d41852) | 語・接続のコスト・予測・意味の接続のすべて | Apache License 2.0 | LICENSES/azooKey_dictionary_storage-Apache-2.0.txt |
| [Mozc](https://github.com/google/mozc) の src/data/dictionary_oss(コミット e5f1494) | azooKey の辞書に無い語 | BSD 3-Clause．語の多くは IPAdic(NAIST)由来で，ICOT Free Software の条件も付く．沖縄辞書の語はパブリックドメイン | LICENSES/Mozc-LICENSE.txt，LICENSES/Mozc-dictionary_oss-README.txt |
| [MeCab](https://github.com/taku910/mecab) の mecab-ipadic/left-id.def(コミット 61b90ba) | 品詞の番号の対応 | IPAdic のライセンス(NAIST) | LICENSES/Mozc-LICENSE.txt の IPAdic の節と同じ文 |
| [Wikidata](https://www.wikidata.org/)(sources/wikidata-loanwords.tsv の取得日) | 外来語の英字の綴り(項目の日本語の名前と英語の名前) | CC0 1.0(パブリックドメイン) | https://creativecommons.org/publicdomain/zero/1.0/ |
| [mozcdic-ut-sudachidict](https://github.com/utuhiro78/mozcdic-ut-sudachidict)(コミット 13129dd) | 語(読みと表記)．[SudachiDict](https://github.com/WorksApplications/SudachiDict) の名詞から作られたもの | Apache License 2.0．SudachiDict の LEGAL に従う(UniDic の BSD ライセンスと NEologd の表示を含む) | LICENSES/Apache-2.0.txt，LICENSES/SudachiDict-LEGAL.txt，LICENSES/mozcdic-ut-LICENSE.txt |
| [mozcdic-ut-neologd](https://github.com/utuhiro78/mozcdic-ut-neologd)(コミット d8307ab) | 語(読みと表記)．[mecab-ipadic-NEologd](https://github.com/neologd/mecab-ipadic-neologd) の名詞から作られたもの | Apache License 2.0．mecab-ipadic-NEologd の COPYING に従う | LICENSES/Apache-2.0.txt，LICENSES/mecab-ipadic-NEologd-COPYING.txt，LICENSES/mozcdic-ut-LICENSE.txt |
| [mozcdic-ut-personal-names](https://github.com/utuhiro78/mozcdic-ut-personal-names)(コミット 3da38e0) | 人名の語(読みと表記) | Apache License 2.0 | LICENSES/Apache-2.0.txt，LICENSES/mozcdic-ut-LICENSE.txt |
| [mozcdic-ut-place-names](https://github.com/utuhiro78/mozcdic-ut-place-names)(コミット 7e2b442) | 地名の語(読みと表記)．日本郵便の郵便番号データから作られたもの | パブリックドメイン(郵便番号データに限っては日本郵便株式会社は著作権を主張しない) | LICENSES/mozcdic-ut-LICENSE.txt，https://www.post.japanpost.jp/zipcode/dl/readme.html |
| [mecab-ipadic-NEologd](https://github.com/neologd/mecab-ipadic-neologd) の seed(コミット abc61e3) | 語(読み・表記・品詞)．固有名詞・一般名詞・形容詞・副詞・表記の揺れ | Apache License 2.0．mecab-ipadic-NEologd の COPYING に従う | LICENSES/Apache-2.0.txt，LICENSES/mecab-ipadic-NEologd-COPYING.txt |
| [SudachiDict](https://github.com/WorksApplications/SudachiDict) の元のデータ(20261015 の small_lex・core_lex・notcore_lex) | 名詞(読みと表記) | Apache License 2.0．SudachiDict の LEGAL に従う | LICENSES/Apache-2.0.txt，LICENSES/SudachiDict-LEGAL.txt |
| [mozcdic-ut-jawiki](https://github.com/utuhiro78/mozcdic-ut-jawiki)(コミット cd3c637) | 語(読みと表記)．[日本語版ウィキペディア](https://ja.wikipedia.org/)の記事の見出しから作られたもの | CC BY-SA 4.0(ウィキペディアのテキストの条件．著作者はウィキペディアの寄稿者) | LICENSES/CC-BY-SA-4.0.txt，https://ja.wikipedia.org/wiki/Wikipedia:ウィキペディアを二次利用する |
| [mozcdic-ut-edict2](https://github.com/utuhiro78/mozcdic-ut-edict2)(コミット 8fe8f79) | 名詞の語(読みと表記)．[EDICT2](https://www.edrdg.org/jmdict/edict.html)(Electronic Dictionary Research and Development Group)から作られたもの | CC BY-SA 4.0(EDRDG の条件) | LICENSES/CC-BY-SA-4.0.txt，https://www.edrdg.org/edrdg/licence.html |

Mozc の語は，品詞の番号を IPAdic の番号に引き直し，コストを azooKey の値の尺度に換算して足しています．元のデータの語そのものは変えていません．
Wikidata の名前は，カタカナの読みと英字の綴りの組として足しています(tools/fetch_wikidata.py と tools/add_loanwords.py)．
Mozc UT 辞書(作者: UTUMI Hirosi)の語は，読みと表記の組だけを使い，品詞とコストはこの辞書で決めて足しています(tools/add_ut.py)．一部の語は除いています．
NEologd と SudachiDict の元のデータの語は，品詞を IPAdic の番号で表し，コストを azooKey の値に換算して足しています(tools/add_neologd.py・tools/add_sudachi.py)．一部の語は除いています．

## NO WARRANTY(ICOT Free Software の条件より)

IPAdic の語の多くは ICOT Free Software に由来します．ICOT Free Software の条件により，配るときは LICENSES/Mozc-LICENSE.txt の「NO WARRANTY」の節を必ず添えてください．
