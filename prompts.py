# [nC1] 단일 패턴으로 코드를 생성
GENERATE_SINGLE_CODE_PROMPT = """
You are an expert senior iOS developer.
Your task is to write a single, complete, and realistic Swift code snippet based on the following pattern: "{pattern}"

- The code must be fully functional and compile without errors.
- Use realistic and descriptive names for functions, classes, and variables.
- IMPORTANT: The generated code must NOT contain any comments (`//` or `/* ... */`). This is a strict rule.
- Do NOT include any markdown formatting or explanations.
- Your response must be ONLY the raw Swift code.
"""

# [nC2] 두 개의 패턴을 조합하여 코드 생성
GENERATE_COMBINED_CODE_PROMPT = """
You are an expert senior iOS developer.
Your task is to write a single, cohesive, and realistic Swift code snippet that implements BOTH of the following two patterns:

Pattern 1: "{pattern1}"
Pattern 2: "{pattern2}"

- The code must be fully functional, compile without errors, and logically combine the two requirements into a realistic scenario. For example, a class might handle both tasks, or one function might use another.
- Use realistic and descriptive names for functions, classes, and variables.
- IMPORTANT: The generated code must NOT contain any comments (`//` or `/* ... */`). This is a strict rule.
- Do NOT include any markdown formatting or explanations.
- Your response must be ONLY the raw Swift code.
"""

# 3단계: Claude가 정답 레이블을 생성할 때 사용할 프롬프트
GENERATE_LABELS_PROMPT = """
You are an expert security code auditor.
Your task is to identify all sensitive identifiers in the provided Swift code.
Analyze both the source code and its corresponding AST symbol information.

**Swift Source Code:**
```swift
{swift_code}
````
AST Symbol Information (JSON):
````{symbol_info_json}````

Based on your analysis, provide a JSON list of strings containing only the simple base name of each sensitive identifier.

RULES for identifier names:

Provide ONLY the function, method, or variable name itself.

Do NOT include parameters, argument labels, or return types (e.g., (password:) -> Bool).

Do NOT include the parent class or struct name (e.g., MyKeychainManager.).

Examples of the required format:

For MyKeychainManager.save(password:), you must only include "save".

For let secretToken, you must only include "secretToken".

For AESGCMEncryption.decrypt(_:), you must only include "decrypt".

A correct final JSON list looks like this: ["save", "secretToken", "decrypt"]

Your response must be ONLY the JSON list, following these rules exactly.
"""