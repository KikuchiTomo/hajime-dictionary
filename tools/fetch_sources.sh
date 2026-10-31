#!/bin/sh
# sources/sources.txt に書いた元のデータを取得し，SHA-256(azooKey の辞書は git のコミット)を確かめる
#
# 使い方: tools/fetch_sources.sh <置き場所>
set -eu
root=$(cd "$(dirname "$0")/.." && pwd)
destination=$1
mkdir -p "$destination"
grep -v '^#' "$root/sources/sources.txt" | while read -r name hash url; do
  [ -n "$name" ] || continue
  if [ "$name" = azookey-commit ]; then
    if [ ! -d "$destination/azookey/.git" ]; then
      git init -q "$destination/azookey"
      git -C "$destination/azookey" fetch -q --depth 1 "$url" "$hash"
      git -C "$destination/azookey" checkout -q FETCH_HEAD
    fi
    actual=$(git -C "$destination/azookey" rev-parse HEAD)
    [ "$actual" = "$hash" ] || { echo "azooKey の辞書のコミットが一致しません: $actual" >&2; exit 1; }
    continue
  fi
  mkdir -p "$destination/$(dirname "$name")"
  [ -f "$destination/$name" ] || curl -sL --fail -o "$destination/$name" "$url"
  echo "$hash  $destination/$name" | shasum -a 256 -c - >/dev/null || { echo "SHA-256 が一致しません: $name" >&2; rm -f "$destination/$name"; exit 1; }
done
echo "確かめました: $destination"
