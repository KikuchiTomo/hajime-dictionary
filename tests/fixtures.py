"""テスト用の小さな辞書(worddict)と IPAdic の品詞の一覧を作る"""
import itertools
import pathlib

KANA = "アイウエオカキクケコサシスセソ"
# tools/add_sudachi.py の NOUN_FEATURES の品詞をすべて含める(足す品詞の番号を引くため)
FEATURES = {
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
