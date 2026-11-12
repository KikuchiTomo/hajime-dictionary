"""テスト用の小さな辞書(worddict)と IPAdic の品詞の一覧を作る"""
import itertools
import pathlib
import zipfile

KANA = "アイウエオカキクケコサシスセソ"
# tools/add_sudachi.py の NOUN_FEATURES の品詞をすべて含める(足す品詞の番号を引くため)
FEATURES = {
    19: "形容詞,自立,*,*,形容詞・アウオ段,基本形,*",
    51: "形容詞,自立,*,*,形容詞・アウオ段,連用テ接続,*",
    1281: "副詞,一般,*,*,*,*,*",
    1285: "名詞,一般,*,*,*,*,*",
    1283: "名詞,サ変接続,*,*,*,*,*",
    1287: "名詞,形容動詞語幹,*,*,*,*,*",
    1288: "名詞,固有名詞,一般,*,*,*,*",
    1289: "名詞,固有名詞,人名,一般,*,*,*",
    1290: "名詞,固有名詞,人名,姓,*,*,*",
    1291: "名詞,固有名詞,人名,名,*,*,*",
    1293: "名詞,固有名詞,地域,一般,*,*,*",
    1294: "名詞,固有名詞,地域,国,*,*,*",
    1314: "名詞,副詞可能,*,*,*,*,*",
}


def readings(count, length=4):
    """重ならないカタカナの読み"""
    return ["".join(p) for p in itertools.islice(itertools.product(KANA, repeat=length), count)]


def write_ipadic(path: pathlib.Path):
    path.write_bytes("".join(f"{n} {f}\n" for n, f in FEATURES.items()).encode("euc_jp"))


def write_worddict(path: pathlib.Path, rows):
    path.write_text("".join(f"{r}\t{w}\t{l}\t{c}\t501\t{v:.4f}\n" for r, w, l, c, v in rows), encoding="utf-8")


def read_worddict(path: pathlib.Path):
    return {(c[0], c[1]): float(c[5]) for c in (line.split("\t") for line in path.read_text(encoding="utf-8").splitlines())}


# テストの語に使う常用漢字．数をそろえるため，ほかに CJK の先頭から常用漢字の数(2136)まで足す
JOYO = "発声生制圧滞注引越素"


def write_unihan(path: pathlib.Path, joyo=JOYO):
    """常用漢字の印(kJoyoKanji)だけを持つ Unihan データベースの zip"""
    characters = list(dict.fromkeys(list(joyo) + [chr(0x4E00 + i) for i in range(2136)]))
    lines = "".join(f"U+{ord(c):04X}\tkJoyoKanji\t2010\n" for c in characters)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("Unihan_OtherMappings.txt", "# kJoyoKanji\n" + lines)
