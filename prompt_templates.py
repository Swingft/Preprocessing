def create_swift_analysis_prompt(module_name, file_path, repo_name, swift_code):
    """Swift 코드 분석용 프롬프트 생성"""
    
    prompt = f"""다음 Swift 라이브러리 코드를 분석해서 두 가지를 생성해줘:

**라이브러리 정보:**
- 모듈명: {module_name}
- 파일경로: {file_path}

**Swift 라이브러리 코드:**
```swift
{swift_code[:6000]}
```

**요청사항:**
1. 위 코드에서 public으로 선언된 모든 API들(클래스/구조체/열거형/함수/메서드/프로퍼티/프로토콜/타입별칭/Extension의 public 멤버들)을 찾아라
2. 찾은 public API들을 **모두** 사용하는 완전한 Swift 사용 예시 코드를 작성해라
3. 사용 예시 코드에서 사용된 외부 라이브러리 식별자들을 JSON으로 정리해라

**출력 형식:**
```swift
// === GENERATED_SWIFT_CODE ===
import {module_name}

// 여기에 찾은 public API들을 모두 사용하는 완전한 예시 코드 작성
class ExampleUsage {{
    func demonstrateAllAPIs() {{
        // 모든 public 클래스, 함수, 메서드, 프로퍼티 사용 예시
    }}
}}
```
```json
// === JSON_LABEL ===
{{
    "module": "{module_name}",
    "file_path": "{file_path}",
    "repo_name": "{repo_name}",
    "external_apis": [
        {{
            "type": "class|struct|enum|func|method|property|protocol|typealias",
            "name": "식별자이름",
            "module": "{module_name}",
            "should_exclude_from_obfuscation": true
        }}
    ]
}}
```
정확히 위 형식으로 Swift 코드와 JSON을 순서대로 출력해줘."""

    return prompt