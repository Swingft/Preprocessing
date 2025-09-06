// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "SwiftASTAnalyzer",
    platforms: [
        .macOS(.v10_15) // 이전 버전과 호환성을 위해 v10_15로 설정
    ],
    dependencies: [
        // 안정성이 검증된 버전으로 의존성 설정
        .package(url: "https://github.com/apple/swift-syntax.git", from: "509.0.0"),
    ],
    targets: [
        // 타겟 이름을 실제 폴더 이름과 일치시킵니다.
        .executableTarget(
            name: "SwiftASTAnalyzer",
            dependencies: [
                .product(name: "SwiftSyntax", package: "swift-syntax"),
                .product(name: "SwiftParser", package: "swift-syntax"),
            ]
        ),
    ]
)