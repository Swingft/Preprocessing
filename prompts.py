# --- 1. Positive Samples (취약한 코드 생성용) ---

# [Positive] nC1 (단일 패턴)으로 취약한 코드를 생성
GENERATE_SINGLE_CODE_PROMPT = """
You are an expert senior iOS developer.
Your task is to write a single, complete, and realistic Swift code snippet that demonstrates the following **vulnerable pattern**: "{pattern}"

- The code must be fully functional and compile without errors.
- Use realistic and descriptive names for functions, classes, and variables.
- IMPORTANT: The generated code must NOT contain any comments (`//` or `/* ... */`). This is a strict rule.
- Do NOT include any markdown formatting or explanations.
- Your response must be ONLY the raw Swift code.
"""

# [Positive] nC2 (두 개의 패턴)으로 취약한 코드를 조합하여 생성
GENERATE_COMBINED_CODE_PROMPT = """
You are an expert senior iOS developer.
Your task is to write a single, cohesive, and realistic Swift code snippet that implements BOTH of the following **vulnerable patterns**:

Pattern 1: "{pattern1}"
Pattern 2: "{pattern2}"

- The code must be fully functional, compile without errors, and logically combine the two requirements into a realistic scenario. For example, a class might handle both tasks, or one function might use another.
- Use realistic and descriptive names for functions, classes, and variables.
- IMPORTANT: The generated code must NOT contain any comments (`//` or `/* ... */`). This is a strict rule.
- Do NOT include any markdown formatting or explanations.
- Your response must be ONLY the raw Swift code.
"""


# --- 2. Negative Samples (안전한 코드 생성용) ---

# [Negative] nC1 (단일 패턴)으로 안전한 코드를 생성
GENERATE_SECURE_SINGLE_CODE_PROMPT = """
You are an expert senior iOS developer with a strong focus on security best practices.
Your task is to write a single, complete, and realistic Swift code snippet that **securely implements** the functionality described in the following pattern: "{pattern}"

- You must demonstrate **best practices** to mitigate the potential vulnerability described.
- For example, if the pattern describes saving a password, you must use the Keychain with strong access controls. If it describes networking, you must use HTTPS and certificate validation.
- IMPORTANT: The code must NOT contain any comments (`//` or `/* ... */`). This is a strict rule.
- Do NOT include any markdown formatting or explanations.
- Your response must be ONLY the raw Swift code.
"""

# [Negative] nC2 (두 개의 패턴)으로 안전한 코드를 조합하여 생성
GENERATE_SECURE_COMBINED_CODE_PROMPT = """
You are an expert senior iOS developer with a strong focus on security best practices.
Your task is to write a single, cohesive, and realistic Swift code snippet that **securely implements** the functionality described in BOTH of the following patterns:

Pattern 1: "{pattern1}"
Pattern 2: "{pattern2}"

- You must demonstrate **best practices** to mitigate the potential vulnerabilities described, combining them into a realistic scenario.
- IMPORTANT: The code must NOT contain any comments (`//` or `/* ... */`). This is a strict rule.
- Do NOT include any markdown formatting or explanations.
- Your response must be ONLY the raw Swift code.
"""

# --- 3. Mixed-Context Samples (혼합형 코드 생성용) ---

# [Mixed-Positive] 민감(취약) + 비민감 로직 혼합
GENERATE_MIXED_CONTEXT_CODE_PROMPT = """
You are an expert iOS developer. Write a single, realistic Swift file that contains BOTH of the following pieces of functionality. The file should represent a typical real-world scenario where sensitive and non-sensitive code coexist.

1.  **Sensitive Logic (Vulnerable Implementation):** "{sensitive_pattern}"
2.  **Non-Sensitive Logic:** "{nonsensitive_pattern}"

- Logically combine the two requirements into a realistic scenario.
- IMPORTANT: The generated code must NOT contain any comments.
- Your response must be ONLY the raw Swift code.
"""

# [Mixed-Negative] 민감(안전) + 비민감 로직 혼합
GENERATE_SECURE_MIXED_CONTEXT_CODE_PROMPT = """
You are an expert iOS developer with a strong focus on security best practices. Write a single, realistic Swift file that contains BOTH of the following pieces of functionality. The file should represent a typical real-world scenario where sensitive and non-sensitive code coexist.

1.  **Sensitive Logic (Secure Implementation):** "{sensitive_pattern}"
2.  **Non-Sensitive Logic:** "{nonsensitive_pattern}"

- Implement the sensitive part using security best practices to mitigate the vulnerability.
- IMPORTANT: The generated code must NOT contain any comments.
- Your response must be ONLY the raw Swift code.
"""

# --- 4. Label Generation (정답 레이블 생성용) ---

# [CoT 적용] 'reasoning' 필드를 포함하도록 구성
GENERATE_LABELS_PROMPT = """
You are an expert security code auditor.
Your task is to identify all sensitive identifiers in the provided Swift code and explain your reasoning.
Analyze both the source code and its corresponding AST symbol information.

**Swift Source Code:**
```swift{swift_code}```

AST Symbol Information (JSON):
```json{symbol_info_json}```Based on your analysis, provide your response as a JSON object with two keys: "reasoning" and "identifiers".

"reasoning": A brief step-by-step explanation of why the identified identifiers are considered sensitive. For secure code, explain why it is safe.

"identifiers": A JSON list of strings containing only the simple base name of each sensitive identifier. For secure code, this should be an empty list [].

Example for vulnerable code:
```json
{
  "reasoning": "The `save` function is sensitive because it calls the `SecItemAdd` Keychain API. The `secretToken` variable holds the data being saved.",
  "identifiers": ["save", "secretToken"]
}
```

Example for secure code:
```json
{
  "reasoning": "This code correctly uses the Keychain to store secrets, which is a security best practice. Therefore, no sensitive identifiers were found.",
  "identifiers": []
}
```
Your response must be ONLY the JSON object, following these rules exactly.
"""

# Negative 샘플의 reasoning을 위한 동적 템플릿
REASONING_TEMPLATE_NEGATIVE = """
This code correctly and securely implements the requested functionality related to '{pattern_text}'. It follows security best practices. Therefore, no sensitive identifiers were found.
"""

