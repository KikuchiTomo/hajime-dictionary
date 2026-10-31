"""azooKey の辞書(louds/*.loudstxt3)の語をすべて TSV に書き出す．

使い方:
    python3 -I tools/dump_azookey.py <Dictionary ディレクトリ> <出力.tsv>

1 行は「読み(カタカナ)<タブ>語<タブ>左 cid<タブ>右 cid<タブ>mid<タブ>コスト」．anco dict build の worddict と同じ列の並び．

loudstxt3 の形(AzooKeyKanaKanjiConverter の Loudstxt3Builder):
- 先頭に項目の数(UInt16)，続いて各項目の始まりの位置(UInt32)
- 項目は，行の数(UInt16)，行ごとに lcid・rcid・mid(UInt16)と score(Float32)，最後に「読み<タブ>語<タブ>語…」の UTF-8
- 語が空なら読みと同じ
すべてリトルエンディアン
"""
import pathlib
import struct
import sys

if len(sys.argv) != 3:
    sys.exit(__doc__)

source = pathlib.Path(sys.argv[1]) / "louds"
destination = sys.argv[2]
ROW = struct.Struct("<HHHf")

count = 0
with open(destination, "w", encoding="utf-8") as output:
    for path in sorted(source.glob("*.loudstxt3")):
        data = path.read_bytes()
        (items,) = struct.unpack_from("<H", data, 0)
        offsets = list(struct.unpack_from(f"<{items}I", data, 2)) + [len(data)]
        for start, end in zip(offsets, offsets[1:]):
            (rows,) = struct.unpack_from("<H", data, start)
            if rows == 0:
                continue
            body = start + 2 + rows * ROW.size
            texts = data[body:end].decode("utf-8").split("\t")
            ruby, words = texts[0], texts[1:]
            if len(words) != rows:
                sys.exit(f"{path.name}: 行の数({rows})と語の数({len(words)})が合いません")
            for index, word in enumerate(words):
                lcid, rcid, mid, score = ROW.unpack_from(data, start + 2 + index * ROW.size)
                output.write(f"{ruby}\t{word or ruby}\t{lcid}\t{rcid}\t{mid}\t{score:.4f}\n")
                count += 1
print(f"{count} 語を書き出しました", file=sys.stderr)
