// swift-tools-version: 6.1
import PackageDescription

let package = Package(
    name: "HajimeDictionaryBuilder",
    platforms: [.macOS(.v14)],
    dependencies: [
        // はじめ(Hajime IME)が使う fork と同じ revision に固定する．辞書の形がこの版の読み込み方と合うようにするため
        .package(
            url: "https://github.com/KikuchiTomo/AzooKeyKanaKanjiConverter",
            revision: "c456c0d4dda385107ac48f666d7ee289710fda25",
            traits: []
        ),
    ],
    targets: [
        .executableTarget(
            name: "build-dictionary",
            dependencies: [.product(name: "KanaKanjiConverterModule", package: "AzooKeyKanaKanjiConverter")]
        ),
    ],
    swiftLanguageModes: [.v6]
)
