"""専門用語の辞書(terms.tsv)の分野と，分野ごとの元のデータ．

分野の id は Hajime IME の設定の項目の名前(termFields.<id>)になる．id を変えたり消したりすると，利用者が切った分野の設定が効かなくなるので，足すだけにする．
分野の名前(「医学」など)は Hajime IME の画面の文言に置く．ここでは README のための日本語の名前だけを持つ

- jmdict: JMdict の語義の分野の印(<field>)．印の付いた語義を持つ語をその分野に入れる
- wikidata: Wikidata のクラス．そのクラスの項目(instance of)と下位のクラス(subclass of)をその分野に入れる(tools/fetch_wikidata_terms.py)
- proper: Wikidata の項目を固有名詞(properNoun)にするか．しなければ名詞(noun)
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Field:
    id: str
    name: str
    jmdict: tuple[str, ...]
    wikidata: tuple[str, ...] = ()
    proper: bool = False


FIELDS = [
    Field("computing", "情報技術", ("comp", "internet", "telec", "audvid"),
          ("Q9143", "Q235557", "Q15836568", "Q8366", "Q175263", "Q9135", "Q37045"), proper=True),
    Field("medicine", "医学", ("med", "anat", "physiol", "psy", "psych", "psyanal", "pharm", "dent", "surg", "pathol", "embryo", "vet"),
          ("Q12136", "Q12140", "Q169872", "Q796194", "Q4936952")),
    # タンパク質(Q8054)と酵素(Q8047)は UniProt の項目が数百万あり，Wikidata Query Service の時間の上限に収まらないので使わない
    Field("biology", "生物学", ("biol", "bot", "zool", "ent", "ornith", "genet", "biochem", "ecol", "paleo"), ("Q11364",)),
    Field("chemistry", "化学", ("chem", "cryst"), ("Q11173", "Q11344", "Q36534")),
    Field("physics", "物理学", ("physics",), ("Q107715", "Q47574", "Q408891")),
    Field("mathematics", "数学", ("math", "geom", "stat", "logic"), ("Q65943", "Q24034552")),
    Field("earth", "地学・天文学", ("astron", "geol", "min", "met", "geogr"), ("Q7946", "Q8063", "Q8928")),
    Field("engineering", "工学", ("engr", "elec", "electr", "mech", "civeng", "aviat", "rail", "mining", "motor"), ("Q11019",)),
    Field("architecture", "建築", ("archit",), ("Q32880", "Q391414")),
    Field("law", "法律・政治", ("law", "politics"), ("Q2135465",)),
    Field("economics", "経済・金融", ("econ", "finc", "stockm"), ("Q169489",)),
    Field("business", "ビジネス", ("bus", "tradem")),
    Field("linguistics", "言語学", ("ling", "gramm")),
    Field("philosophy", "哲学・思想", ("phil",), ("Q1387659",)),
    Field("religion", "宗教・神話", ("Buddh", "Christn", "Shinto", "grmyth", "jpmyth", "rommyth", "chmyth"), ("Q178885",), proper=True),
    Field("music", "音楽", ("music",), ("Q34379", "Q188451")),
    Field("design", "美術・デザイン", ("art", "print", "photo", "cloth"), ("Q17451", "Q968159")),
    Field("food", "料理・食品", ("food",), ("Q746549", "Q40050")),
    Field("sports", "スポーツ", ("sports", "baseb", "sumo", "MA", "golf", "boxing", "ski", "prowres", "figskt", "horse"), ("Q349", "Q31629")),
    Field("games", "囲碁・将棋・ゲーム", ("go", "shogi", "mahj", "cards", "hanaf", "vidg"), ("Q131436", "Q142714")),
    Field("military", "軍事", ("mil",), ("Q728",)),
    Field("agriculture", "農林水産", ("agric", "fish", "gardn")),
    Field("performingArts", "芸能・映像", ("kabuki", "noh", "film", "tv", "manga")),
    Field("history", "歴史・考古学", ("archeol",)),
]

BY_JMDICT = {tag: f.id for f in FIELDS for tag in f.jmdict}
