# NOTICE

この辞書は，次のデータを組み合わせて作っています．配るときはこのファイルと LICENSES/ を添えてください．

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

Mozc の語は，品詞の番号を IPAdic の番号に引き直し，コストを azooKey の値の尺度に換算して足しています．元のデータの語そのものは変えていません．
Wikidata の名前は，カタカナの読みと英字の綴りの組として足しています(tools/fetch_wikidata.py と tools/add_loanwords.py)．
Mozc UT 辞書(作者: UTUMI Hirosi)の語は，読みと表記の組だけを使い，品詞とコストはこの辞書で決めて足しています(tools/add_ut.py)．一部の語は除いています．

## NO WARRANTY(ICOT Free Software の条件より)

IPAdic の語の多くは ICOT Free Software に由来します．ICOT Free Software の条件により，配るときは LICENSES/Mozc-LICENSE.txt の「NO WARRANTY」の節を必ず添えてください．
