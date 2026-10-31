#!/bin/sh
# 辞書を作り，配布物(dist/hajime-dictionary-<版>.tar.gz)にする．
# 元のデータの取得と確認 → azooKey の辞書の書き出し → Mozc の語を足す → LOUDS を作る → ライセンスの表示を添えて固める
#
# 使い方: ./build.sh <版(例: 0.1.0)> [作業の置き場所(既定: work/)]
set -eu
root=$(cd "$(dirname "$0")" && pwd)
version=$1
work=${2:-"$root/work"}
# Mozc だけにある語のうち，足す読みの長さの下限．短い読みのまれな語が既存の語を押しのけるため(README の「作り方」)
min_reading_length=4

"$root/tools/fetch_sources.sh" "$work/sources"
azookey="$work/sources/azookey/Dictionary"
python3 -I "$root/tools/dump_azookey.py" "$azookey" "$work/azookey.tsv"
python3 -I "$root/tools/merge_mozc.py" "$work/azookey.tsv" "$work/sources/mozc" "$work/sources/ipadic/left-id.def" "$work/worddict.tsv" \
  --min-reading-length "$min_reading_length"
package="$work/package/hajime-dictionary-$version"
rm -rf "$work/package"
"$root/tools/assemble.sh" "$work/worddict.tsv" "$azookey" "$package/Dictionary"
# 辞書のファイルごとの SHA-256 の一覧．使う側は一覧の SHA-256 を持っておき，一覧と各ファイルを確かめてから読む
(cd "$package/Dictionary" && find . -type f ! -name SHA256SUMS | sed 's|^\./||' | LC_ALL=C sort | while read -r file; do shasum -a 256 "$file"; done > SHA256SUMS)
cp -R "$root/LICENSES" "$root/NOTICE.md" "$package/"
printf '%s\n' "$version" > "$package/VERSION"
mkdir -p "$root/dist"
# 中身の並び・時刻・持ち主をそろえ，gzip にも時刻を入れず，同じ元のデータから同じファイルができるようにする
(cd "$work/package" && find "hajime-dictionary-$version" -exec touch -h -t 202601010000 {} + && \
  find "hajime-dictionary-$version" -type f | LC_ALL=C sort > files.txt && \
  tar --uid 0 --gid 0 --uname root --gname root -cf - -T files.txt | gzip -n -9 > "$root/dist/hajime-dictionary-$version.tar.gz")
(cd "$root/dist" && shasum -a 256 "hajime-dictionary-$version.tar.gz" > "hajime-dictionary-$version.tar.gz.sha256")
cat "$root/dist/hajime-dictionary-$version.tar.gz.sha256"
