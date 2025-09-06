import Foundation
import SwiftSyntax
import SwiftParser

// MARK: - 1. 최종 데이터 모델
// 빈 배열은 JSON 출력에서 제외되도록 Encodable을 직접 구현합니다.
struct SymbolInfo: Encodable {
    let symbolName: String
    let symbolKind: String
    let typeSignature: String
    let calls_out: [String]
    let references: [String]
    let conforms: [String]
    let attributes: [String]

    enum CodingKeys: String, CodingKey {
        case symbolName, symbolKind, typeSignature, calls_out, references, conforms, attributes
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(symbolName, forKey: .symbolName)
        try container.encode(symbolKind, forKey: .symbolKind)
        if !typeSignature.isEmpty {
            try container.encode(typeSignature, forKey: .typeSignature)
        }
        if !calls_out.isEmpty {
            try container.encode(calls_out, forKey: .calls_out)
        }
        if !references.isEmpty {
            try container.encode(references, forKey: .references)
        }
        if !conforms.isEmpty {
            try container.encode(conforms, forKey: .conforms)
        }
        if !attributes.isEmpty {
            try container.encode(attributes, forKey: .attributes)
        }
    }
}


// MARK: - Utilities
func collectAttributes(_ attrs: AttributeListSyntax?) -> [String] {
    guard let attrs = attrs else { return [] }
    return attrs.compactMap { attr in
        if let a = attr.as(AttributeSyntax.self) {
            return "@\(a.attributeName.trimmedDescription)"
        }
        return nil
    }
}

func inheritsFrom(_ clause: InheritanceClauseSyntax?) -> [String] {
    guard let clause = clause else { return [] }
    return clause.inheritedTypes.map { $0.type.trimmedDescription }
}

func funcTypeSignature(_ decl: FunctionDeclSyntax) -> String {
    decl.signature.trimmedDescription
}

func varTypeSignature(_ decl: VariableDeclSyntax) -> String {
    if let binding = decl.bindings.first, let typeAnno = binding.typeAnnotation {
        return typeAnno.type.trimmedDescription
    }
    return ""
}

func propertyNames(_ decl: VariableDeclSyntax) -> [String] {
    decl.bindings.compactMap {
        $0.pattern.as(IdentifierPatternSyntax.self)?.identifier.text
    }
}

func qualTypeName(stack: [String], currentType: String?) -> String {
    (stack + [currentType].compactMap { $0 }).joined(separator: ".")
}


// MARK: - Body scan visitor
final class BodyVisitor: SyntaxVisitor {
    var calls: [String] = []
    var refs: [String] = []

    override func visit(_ node: FunctionCallExprSyntax) -> SyntaxVisitorContinueKind {
        if let calledExpr = node.calledExpression.as(DeclReferenceExprSyntax.self) {
            calls.append(calledExpr.baseName.text)
        } else if let memberAccess = node.calledExpression.as(MemberAccessExprSyntax.self) {
            calls.append(memberAccess.declName.baseName.text)
        }
        return .visitChildren
    }

    override func visit(_ node: DeclReferenceExprSyntax) -> SyntaxVisitorContinueKind {
        refs.append(node.baseName.text)
        return .visitChildren
    }

    override func visit(_ node: MemberAccessExprSyntax) -> SyntaxVisitorContinueKind {
        refs.append(node.declName.baseName.text)
        return .visitChildren
    }
}

private func scanBodySignals(_ syntax: Syntax) -> (calls:[String], refs:[String]) {
    let v = BodyVisitor(viewMode: .sourceAccurate)
    v.walk(syntax)
    func uniq(_ a:[String]) -> [String] { Array(Set(a)).sorted() }
    return (uniq(v.calls), uniq(v.refs))
}


// MARK: - Main Visitor
final class SymbolCollector: SyntaxVisitor {
    private var typeStack: [String] = []
    var symbols: [SymbolInfo] = []

    // SwiftSyntax API 변경에 따라 'SyntaxTreeViewMode'를 사용하도록 수정
    override init(viewMode: SyntaxTreeViewMode) {
        super.init(viewMode: viewMode)
    }

    // MARK: Type Decls
    override func visit(_ node: ClassDeclSyntax) -> SyntaxVisitorContinueKind {
        typeStack.append(node.name.text)
        defer { _ = typeStack.popLast() }

        let qualName = qualTypeName(stack: typeStack.dropLast().map{$0}, currentType: node.name.text)
        let info = SymbolInfo(
            symbolName: qualName,
            symbolKind: "class",
            typeSignature: "",
            calls_out: [],
            references: [],
            conforms: inheritsFrom(node.inheritanceClause),
            attributes: collectAttributes(node.attributes)
        )
        symbols.append(info)
        return .visitChildren
    }

    override func visit(_ node: StructDeclSyntax) -> SyntaxVisitorContinueKind {
        typeStack.append(node.name.text)
        defer { _ = typeStack.popLast() }

        let qualName = qualTypeName(stack: typeStack.dropLast().map{$0}, currentType: node.name.text)
        let info = SymbolInfo(
            symbolName: qualName,
            symbolKind: "struct",
            typeSignature: "",
            calls_out: [],
            references: [],
            conforms: inheritsFrom(node.inheritanceClause),
            attributes: collectAttributes(node.attributes)
        )
        symbols.append(info)
        return .visitChildren
    }

    // MARK: Members
    override func visit(_ node: FunctionDeclSyntax) -> SyntaxVisitorContinueKind {
        let sig = funcTypeSignature(node)
        let name = node.name.text
        let qualBase = qualTypeName(stack: typeStack, currentType: nil)
        let qualName = (qualBase.isEmpty ? "" : "\(qualBase).") + name

        let bodySyntax: Syntax = node.body.map { Syntax($0) } ?? Syntax(node)
        let (calls, refs) = scanBodySignals(bodySyntax)

        let info = SymbolInfo(
            symbolName: "\(qualName)(\(sig))",
            symbolKind: "method",
            typeSignature: sig,
            calls_out: calls,
            references: refs,
            conforms: [],
            attributes: collectAttributes(node.attributes)
        )
        symbols.append(info)
        return .visitChildren
    }

    override func visit(_ node: VariableDeclSyntax) -> SyntaxVisitorContinueKind {
        let sig = varTypeSignature(node)
        let names = propertyNames(node)
        let (calls, refs) = node.bindings.first?.accessorBlock.map { scanBodySignals(Syntax($0)) } ?? ([], [])
        let qualPrefix = qualTypeName(stack: typeStack, currentType: nil)
        let isGlobal = typeStack.isEmpty
        let kind = isGlobal ? "variable" : "property"

        for n in names {
            let qn = (qualPrefix.isEmpty ? "" : "\(qualPrefix).") + n
            let info = SymbolInfo(
                symbolName: qn,
                symbolKind: kind,
                typeSignature: sig,
                calls_out: calls,
                references: refs,
                conforms: [],
                attributes: collectAttributes(node.attributes)
            )
            symbols.append(info)
        }
        return .visitChildren
    }
}


// MARK: - Runner
func analyzeSwiftFile(path: String) -> [SymbolInfo] {
    guard let source = try? String(contentsOfFile: path, encoding: .utf8) else {
        return []
    }
    let tree = Parser.parse(source: source)
    // SwiftSyntax API 변경에 따라 'SyntaxTreeViewMode'를 사용하도록 수정
    let collector = SymbolCollector(viewMode: .sourceAccurate)
    collector.walk(tree)
    return collector.symbols
}


// MARK: - Main
if CommandLine.arguments.count < 2 {
    fputs("Usage: \(CommandLine.arguments[0]) <file-to-analyze.swift>\n", stderr)
    exit(1)
}

let inputPath = CommandLine.arguments[1]
let symbols = analyzeSwiftFile(path: inputPath)

let encoder = JSONEncoder()
encoder.outputFormatting = .prettyPrinted

do {
    let jsonData = try encoder.encode(symbols)
    if let jsonString = String(data: jsonData, encoding: .utf8) {
        print(jsonString)
    }
} catch {
    fputs("Error encoding JSON: \(error)\n", stderr)
    exit(1)
}