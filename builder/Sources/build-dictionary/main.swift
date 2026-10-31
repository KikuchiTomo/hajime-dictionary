import Foundation
import KanaKanjiConverterModule

// worddict の TSV(読み<タブ>語<タブ>左 cid<タブ>右 cid<タブ>mid<タブ>値)から，azooKey の louds/ を作る．
//
// 使い方: build-dictionary <worddict.tsv> <charID.chid> <出力の louds ディレクトリ>
//
// 読みの先頭の文字ごとにファイルを分ける(azooKey の既定の辞書と同じ並べ方)．
// charID.chid に無い文字を含む読みの語は DictionaryBuilder が飛ばす
let arguments = CommandLine.arguments
guard arguments.count == 4 else {
    FileHandle.standardError.write(Data("使い方: build-dictionary <worddict.tsv> <charID.chid> <出力の louds ディレクトリ>\n".utf8))
    exit(2)
}
let source = URL(fileURLWithPath: arguments[1])
let charID = URL(fileURLWithPath: arguments[2])
let destination = URL(fileURLWithPath: arguments[3], isDirectory: true)

var entries: [DicdataElement] = []
let text = try String(contentsOf: source, encoding: .utf8)
for line in text.split(separator: "\n") {
    let columns = line.split(separator: "\t", omittingEmptySubsequences: false)
    guard columns.count == 6, let lcid = Int(columns[2]), let rcid = Int(columns[3]), let mid = Int(columns[4]), let value = Float(columns[5]) else {
        FileHandle.standardError.write(Data("形の正しくない行があります: \(line.prefix(80))\n".utf8))
        exit(1)
    }
    entries.append(DicdataElement(word: String(columns[1]), ruby: String(columns[0]), lcid: lcid, rcid: rcid, mid: mid, value: PValue(value)))
}

try FileManager.default.createDirectory(at: destination, withIntermediateDirectories: true)
try DictionaryBuilder.exportDictionary(entries: entries, to: destination, baseName: "", shardByFirstCharacter: true, charIDFileURL: charID)
try FileManager.default.copyItem(at: charID, to: destination.appendingPathComponent("charID.chid"))
print("\(entries.count) 語から louds を作りました: \(destination.path)")
