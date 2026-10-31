#!/bin/sh
# worddict の TSV から辞書のディレクトリ一式を作る．louds/ は作り直し，接続のコスト(cb/)・予測(p/)・意味の接続(mm.binary)は azooKey の辞書のものを使う
#
# 使い方: tools/assemble.sh <worddict.tsv> <azooKey の Dictionary ディレクトリ> <出力ディレクトリ>
set -eu
root=$(cd "$(dirname "$0")/.." && pwd)
source=$1
azookey=$2
destination=$3
rm -rf "$destination"
mkdir -p "$destination"
swift build --package-path "$root/builder" -c release >/dev/null
"$(swift build --package-path "$root/builder" -c release --show-bin-path)/build-dictionary" "$source" "$azookey/louds/charID.chid" "$destination/louds"
cp -R "$azookey/cb" "$azookey/p" "$destination/"
cp "$azookey/mm.binary" "$destination/"
