# NOTICE

この辞書は，次のデータを組み合わせて作っています．配るときはこのファイルと LICENSES/ を添えてください．

| 元のデータ | 使ったもの | ライセンス | 全文 |
|---|---|---|---|
| [azooKey_dictionary_storage](https://github.com/ensan-hcl/azooKey_dictionary_storage)(コミット 4d41852) | 語・接続のコスト・予測・意味の接続のすべて | Apache License 2.0 | LICENSES/azooKey_dictionary_storage-Apache-2.0.txt |
| [Mozc](https://github.com/google/mozc) の src/data/dictionary_oss(コミット e5f1494) | azooKey の辞書に無い語 | BSD 3-Clause．語の多くは IPAdic(NAIST)由来で，ICOT Free Software の条件も付く．沖縄辞書の語はパブリックドメイン | LICENSES/Mozc-LICENSE.txt，LICENSES/Mozc-dictionary_oss-README.txt |
| [MeCab](https://github.com/taku910/mecab) の mecab-ipadic/left-id.def(コミット 61b90ba) | 品詞の番号の対応 | IPAdic のライセンス(NAIST) | LICENSES/Mozc-LICENSE.txt の IPAdic の節と同じ文 |
| [Wikidata](https://www.wikidata.org/)(sources/wikidata-loanwords.tsv の取得日) | 外来語の英字の綴り(項目の日本語の名前と英語の名前) | CC0 1.0(パブリックドメイン) | https://creativecommons.org/publicdomain/zero/1.0/ |

Mozc の語は，品詞の番号を IPAdic の番号に引き直し，コストを azooKey の値の尺度に換算して足しています．元のデータの語そのものは変えていません．
Wikidata の名前は，カタカナの読みと英字の綴りの組として足しています(tools/fetch_wikidata.py と tools/add_loanwords.py)．

## NO WARRANTY(ICOT Free Software の条件より)

IPAdic の語の多くは ICOT Free Software に由来します．ICOT Free Software の条件により，配るときは LICENSES/Mozc-LICENSE.txt の「NO WARRANTY」の節を必ず添えてください．
