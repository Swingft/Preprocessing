import time
import re
import json
import subprocess
import tempfile
from pathlib import Path
from tqdm import tqdm
import itertools
import random
import concurrent.futures
from prompts import (
    GENERATE_SINGLE_CODE_PROMPT, GENERATE_COMBINED_CODE_PROMPT,
    GENERATE_SECURE_SINGLE_CODE_PROMPT, GENERATE_SECURE_COMBINED_CODE_PROMPT,
    GENERATE_MIXED_CONTEXT_CODE_PROMPT, GENERATE_SECURE_MIXED_CONTEXT_CODE_PROMPT
)
from claude_handler.claude_handler import ClaudeHandler  # 코드 생성용
from gemini_handler.gemini_handler import GeminiHandler  # 코드 생성 + 레이블 생성용

# --- 테스트 전용 설정 ---
ANALYZER_EXECUTABLE = "./SwiftASTAnalyzer/.build/release/SwiftASTAnalyzer"
PATTERNS_FILE = "./patterns.json"
OUTPUT_DIR = Path("./output")

# 테스트 디렉토리 기본 경로 (기존 구조와 동일)
TEST_BASE_DIR = OUTPUT_DIR / "generated_code" / "test"
TEST_INPUTS_BASE_DIR = OUTPUT_DIR / "inputs" / "test"
TEST_OUTPUTS_BASE_DIR = OUTPUT_DIR / "outputs" / "test"


# --- 헬퍼 함수들 ---

def get_test_projects() -> list:
    """test 디렉토리 내의 모든 프로젝트 폴더를 지정된 순서로 반환합니다."""
    # 처리 순서 강제: UIKit+SPM_2 -> ConfettiSwiftUI -> iOS -> UIKit+SPM_1
    priority_order = [
        "Code_UIKit+SPM_2_combined",
        "Code_ConfettiSwiftUI",
        "Code_iOS",
        "Code_UIKit+SPM_1_combined"
    ]

    test_projects = []
    if TEST_BASE_DIR.exists():
        existing_projects = set()
        for item in TEST_BASE_DIR.iterdir():
            if item.is_dir():
                existing_projects.add(item.name)

        # 우선순위 순서대로 추가
        for project in priority_order:
            if project in existing_projects:
                test_projects.append(project)
                existing_projects.remove(project)

        # 나머지 프로젝트들은 알파벳 순으로 추가
        for project in sorted(existing_projects):
            test_projects.append(project)

    return test_projects


def get_test_project_paths(project_name: str) -> dict:
    """테스트 프로젝트의 디렉토리 경로를 반환합니다."""
    return {
        "code": TEST_BASE_DIR / project_name,
        "inputs": TEST_INPUTS_BASE_DIR / project_name,
        "labels": TEST_OUTPUTS_BASE_DIR / project_name
    }


def discover_existing_test_files():
    """모든 테스트 프로젝트에서 기존 Swift 파일들을 발견합니다."""
    test_tasks = []
    test_projects = get_test_projects()

    print(f"📁 테스트 프로젝트들에서 기존 Swift 파일 검색 중...")

    for project in test_projects:
        project_code_dir = TEST_BASE_DIR / project
        if not project_code_dir.exists():
            print(f"  - {project}: 디렉토리가 존재하지 않습니다")
            continue

        swift_files = list(project_code_dir.glob("*.swift"))
        print(f"  - {project}: {len(swift_files)}개의 Swift 파일 발견")

        for swift_file in swift_files:
            task_name = swift_file.stem
            test_tasks.append({
                "project": project,
                "filename": task_name,
                "file_path": swift_file,
                "type": "Existing_Code"
            })

    return test_tasks


def extract_json_block(text: str) -> str | None:
    """텍스트에서 JSON 블록을 안전하게 추출합니다."""
    if not text or not isinstance(text, str):
        return None

    text = text.strip()

    # 1. ```json ... ``` 블록 검색
    json_block_patterns = [
        r"```json\s*(\{.*?\})\s*```",
        r"```\s*(\{.*?\})\s*```",
        r"```json\s*([\s\S]*?)\s*```",
        r"```\s*([\s\S]*?)\s*```"
    ]

    for pattern in json_block_patterns:
        try:
            match = re.search(pattern, text, re.DOTALL | re.MULTILINE)
            if match:
                json_candidate = match.group(1).strip()
                if json_candidate and validate_and_return_json(json_candidate):
                    return json_candidate
        except Exception:
            continue

    # 2. 블록 마커 없이 JSON 객체 찾기
    return extract_json_from_text(text)


def extract_json_from_text(text: str) -> str | None:
    """텍스트에서 유효한 JSON 객체를 추출합니다."""
    try:
        # 줄별로 처리하여 JSON 시작점 찾기
        lines = text.split('\n')
        json_start_line = -1

        # JSON이 시작될 것 같은 라인 찾기
        for i, line in enumerate(lines):
            stripped_line = line.strip()
            if stripped_line.startswith('{'):
                json_start_line = i
                break

        if json_start_line == -1:
            return None

        # JSON 끝점 찾기 (중괄호 균형)
        brace_count = 0
        json_lines = []

        for i in range(json_start_line, len(lines)):
            line = lines[i]
            json_lines.append(line)

            for char in line:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1

            if brace_count == 0 and len(json_lines) > 0:
                # JSON 객체가 완성됨
                json_text = '\n'.join(json_lines)
                return validate_and_return_json(json_text.strip())

        # 중괄호가 균형을 이루지 못한 경우, 전체 텍스트에서 JSON 시도
        return validate_and_return_json(text)

    except Exception:
        return None


def validate_and_return_json(json_text: str) -> str | None:
    """JSON 텍스트의 유효성을 검사하고 반환합니다."""
    if not json_text:
        return None

    try:
        # 앞뒤 공백 및 특수문자 제거
        json_text = json_text.strip()

        # JSON 파싱 시도
        parsed = json.loads(json_text)

        # 기대하는 구조 확인 (reasoning, identifiers 필드)
        if isinstance(parsed, dict) and "reasoning" in parsed and "identifiers" in parsed:
            # 유효한 JSON이므로 원본 반환 (포맷팅 보존)
            return json_text

    except (json.JSONDecodeError, TypeError, AttributeError) as e:
        # JSON 파싱 실패 - 일반적인 문제들을 수정 시도
        try:
            # 흔한 문제들 수정
            fixed_json = fix_common_json_issues(json_text)
            if fixed_json and fixed_json != json_text:
                parsed = json.loads(fixed_json)
                if isinstance(parsed, dict) and "reasoning" in parsed and "identifiers" in parsed:
                    return fixed_json
        except Exception:
            pass

    return None


def fix_common_json_issues(json_text: str) -> str:
    """일반적인 JSON 형식 문제들을 수정합니다."""
    if not json_text:
        return json_text

    try:
        # 1. 앞뒤 불필요한 문자 제거
        json_text = json_text.strip()

        # 2. 시작과 끝이 중괄호가 아닌 경우 찾기
        start_idx = json_text.find('{')
        end_idx = json_text.rfind('}')

        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_text = json_text[start_idx:end_idx + 1]

        # 3. 따옴표 문제 수정 (단순한 경우만)
        json_text = re.sub(r'([{,]\s*)(\w+)(\s*:)', r'\1"\2"\3', json_text)

        # 4. 후행 쉼표 제거
        json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)

        return json_text

    except Exception:
        return json_text


def run_swift_analyzer_on_code(swift_code: str) -> str | None:
    """Swift 코드를 임시 파일에 저장하고 분석기를 실행하여 심볼 정보를 반환합니다."""
    if not swift_code or not swift_code.strip():
        return None

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file_path = Path(temp_dir) / "temp.swift"
            temp_file_path.write_text(swift_code, encoding='utf-8')
            command = [ANALYZER_EXECUTABLE, str(temp_file_path.absolute())]

            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
                encoding='utf-8',
                timeout=30
            )
            return process.stdout.strip() if process.stdout else None

    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, Exception) as e:
        print(f"  ⚠️ Swift analyzer failed: {e}")
        return None


def create_alpaca_input(swift_code: str, symbol_info_json: str) -> str:
    """모델이 학습할 Input 필드를 형식에 맞게 생성합니다."""
    try:
        symbol_info_pretty = json.dumps(json.loads(symbol_info_json), indent=2, ensure_ascii=False)
    except (json.JSONDecodeError, TypeError):
        symbol_info_pretty = symbol_info_json

    return f"""**Swift Source Code:**
```swift
{swift_code}
```

**AST Symbol Information (JSON):**
```
{symbol_info_pretty}
```"""


def safe_gemini_label_request(prompt: str, max_retries: int = 3) -> str:
    """Gemini API 요청을 안전하게 처리합니다 (레이블 생성용)."""
    for attempt in range(max_retries):
        try:
            prompt_config = {
                "messages": [
                    {
                        "role": "user",
                        "parts": [prompt]
                    }
                ]
            }
            response = GeminiHandler.ask(prompt_config, model_name="gemini-2.5-pro")
            if response and response.strip():
                return response.strip()
        except Exception as e:
            print(f"  ⚠️ Gemini label request attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    return ""


def process_existing_test_file(test_task: dict):
    """기존 테스트 파일을 처리하여 라벨을 생성합니다."""
    project = test_task["project"]
    filename = test_task["filename"]
    file_path = test_task["file_path"]

    paths = get_test_project_paths(project)
    code_path = paths["code"] / f"{filename}.swift"
    input_path = paths["inputs"] / f"{filename}.txt"
    label_path = paths["labels"] / f"{filename}.json"

    # 이미 유효한 라벨이 있으면 스킵
    try:
        if label_path.exists() and label_path.stat().st_size > 10:
            content = label_path.read_text(encoding='utf-8').strip()
            if content:
                json.loads(content)  # JSON 유효성 검사
                print(f"  - [TEST/{project}] `{filename}` - 이미 처리됨, 스킵")
                return
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        pass

    print(f"  - [TEST/{project}] `{filename}` 처리 중...")

    # Swift 코드 읽기
    try:
        swift_code = code_path.read_text(encoding='utf-8')
        if not swift_code or not swift_code.strip():
            print(f"    ❌ Swift 코드가 비어있음")
            return
    except Exception as e:
        print(f"    ❌ Swift 코드 읽기 실패: {e}")
        return

    # AST 분석
    symbol_info_json = run_swift_analyzer_on_code(swift_code)
    if not symbol_info_json:
        print(f"    ❌ Swift analyzer 실패 또는 유효하지 않은 JSON 반환")
        return

    # 라벨 생성용 프롬프트 생성 및 저장
    try:
        label_prompt = f"""You are an expert security code auditor.
Your task is to identify all sensitive identifiers in the provided Swift code and explain your reasoning.
Analyze both the source code and its corresponding AST symbol information.

**Swift Source Code:**
```swift
{swift_code}
```

**AST Symbol Information (JSON):**
```json
{symbol_info_json}
```

Based on your analysis, provide your response as a JSON object with two keys: "reasoning" and "identifiers".

"reasoning": A brief step-by-step explanation of why the identified identifiers are considered sensitive. For secure code, explain why it is safe.

"identifiers": A JSON list of strings containing only the simple base name of each sensitive identifier. For secure code, this should be an empty list [].

Example for vulnerable code:
```json
{{
  "reasoning": "The `save` function is sensitive because it calls the `SecItemAdd` Keychain API. The `secretToken` variable holds the data being saved.",
  "identifiers": ["save", "secretToken"]
}}
```

Example for secure code:
```json
{{
  "reasoning": "This code correctly uses the Keychain to store secrets, which is a security best practice. Therefore, no sensitive identifiers were found.",
  "identifiers": []
}}
```

Your response must be ONLY the JSON object, following these rules exactly."""

        input_path.write_text(label_prompt, encoding='utf-8')
    except Exception as e:
        print(f"    ❌ 입력 프롬프트 저장 실패: {e}")
        return

    # 라벨 생성 (Gemini 사용)
    success = False
    final_output_json_str = ""

    for attempt in range(3):
        try:
            raw_response = safe_gemini_label_request(label_prompt)
            if not raw_response:
                print(f"    ⚠️ Empty response for {project}/{filename}, attempt {attempt + 1}")
                continue

            print(f"    🔍 Raw response length for {project}/{filename}: {len(raw_response)} chars")

            # 여러 방법으로 JSON 추출 시도
            json_candidates = []

            # 방법 1: 기존 extract_json_block
            extracted_json = extract_json_block(raw_response)
            if extracted_json:
                json_candidates.append(extracted_json)

            # 방법 2: 간단한 중괄호 찾기
            start = raw_response.find('{')
            end = raw_response.rfind('}')
            if start != -1 and end != -1 and end > start:
                simple_json = raw_response[start:end + 1]
                if simple_json not in json_candidates:
                    json_candidates.append(simple_json)

            # 각 후보에 대해 검증
            for candidate in json_candidates:
                try:
                    output_data = json.loads(candidate)
                    if isinstance(output_data, dict) and "reasoning" in output_data and "identifiers" in output_data:
                        final_output_json_str = json.dumps(output_data, ensure_ascii=False, indent=2)
                        success = True
                        print(f"    ✅ JSON successfully parsed for {project}/{filename}")
                        break
                except json.JSONDecodeError as e:
                    print(f"    ⚠️ JSON candidate failed for {project}/{filename}: {e}")
                    continue

            if success:
                break
            else:
                print(f"    ❌ All JSON candidates failed for {project}/{filename}, attempt {attempt + 1}")
                print(f"    📄 Response preview: {raw_response[:200]}...")
                time.sleep(2)

        except Exception as e:
            print(f"    ⚠️ Unexpected error for {project}/{filename}, attempt {attempt + 1}: {e}")
            time.sleep(2)

    if not success:
        print(f"    ❌ Label generation failed for {project}/{filename} after 3 attempts.")
        try:
            label_path.write_text('{"error": "generation_failed"}', encoding='utf-8')
        except Exception:
            pass
        return

    # 최종 저장
    try:
        label_path.write_text(final_output_json_str, encoding='utf-8')
        print(f"    ✅ `{filename}` 처리 완료")
    except Exception as e:
        print(f"    ❌ 라벨 저장 실패: {e}")
        return


def assemble_test_datasets():
    """테스트 프로젝트별로 최종 데이터셋을 조립합니다."""
    print("\n📦 테스트 데이터셋 조립 중...")

    test_projects = get_test_projects()
    all_test_data = []
    project_counts = {}

    for project in test_projects:
        print(f"\n  - {project} 프로젝트 처리 중...")

        paths = get_test_project_paths(project)
        label_files = sorted(list(paths["labels"].glob("*.json")))

        if not label_files:
            print(f"    라벨 파일 없음")
            project_counts[project] = 0
            continue

        project_data = []
        success_count = 0
        error_count = 0

        for label_path in tqdm(label_files, desc=f"{project} 데이터셋 조립"):
            try:
                # 유효한 JSON 파일인지 확인
                try:
                    if not label_path.exists() or label_path.stat().st_size <= 10:
                        error_count += 1
                        continue
                    content = label_path.read_text(encoding='utf-8').strip()
                    if not content or content == "":
                        error_count += 1
                        continue
                    json.loads(content)  # JSON 유효성 검사
                except (json.JSONDecodeError, UnicodeDecodeError, OSError):
                    error_count += 1
                    continue

                code_path = paths["code"] / (label_path.stem + ".swift")
                input_path = paths["inputs"] / (label_path.stem + ".txt")

                if not code_path.exists() or not input_path.exists():
                    error_count += 1
                    continue

                swift_code = code_path.read_text(encoding='utf-8')
                if not swift_code or not swift_code.strip():
                    error_count += 1
                    continue

                output_json_str = label_path.read_text(encoding='utf-8')
                input_prompt = input_path.read_text(encoding='utf-8')

                # input 프롬프트에서 symbol_info를 추출
                symbol_info_json = None
                if "AST Symbol Information (JSON):" in input_prompt:
                    match = re.search(r'AST Symbol Information \(JSON\):\s*```\s*(.*?)\s*```', input_prompt, re.DOTALL)
                    if match:
                        symbol_info_json = match.group(1).strip()

                # 만약 추출에 실패하면 Swift analyzer 다시 실행
                if not symbol_info_json:
                    symbol_info_json = run_swift_analyzer_on_code(swift_code)
                    if not symbol_info_json:
                        error_count += 1
                        continue

                # JSON 파싱 검증
                try:
                    symbol_info_dict = json.loads(symbol_info_json)
                    output_dict = json.loads(output_json_str)
                except json.JSONDecodeError:
                    error_count += 1
                    continue

                # 최종 데이터셋 엔트리 생성
                entry = {
                    "instruction": "In the following Swift code, find all identifiers related to sensitive logic. Provide the names and reasoning as a JSON object.",
                    "input": create_alpaca_input(swift_code, symbol_info_json),
                    "output": output_json_str
                }

                project_data.append(entry)
                all_test_data.append(entry)
                success_count += 1

            except Exception as e:
                error_count += 1
                print(f"\n⚠️ 파일 조립 중 에러 발생 '{label_path.name}': {e}")

        project_counts[project] = success_count
        print(f"    {success_count}개 성공, {error_count}개 실패")

        # 프로젝트별 데이터셋 파일 저장
        if project_data:
            try:
                project_dataset_file = OUTPUT_DIR / f"test_{project}_dataset.jsonl"
                with open(project_dataset_file, "w", encoding="utf-8") as f:
                    for entry in project_data:
                        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                print(f"    저장됨: {project_dataset_file}")
            except Exception as e:
                print(f"    ❌ 프로젝트 데이터셋 저장 실패: {e}")

    # 전체 테스트 데이터셋 저장
    if all_test_data:
        try:
            all_test_dataset_file = OUTPUT_DIR / "all_test_dataset.jsonl"
            with open(all_test_dataset_file, "w", encoding="utf-8") as f:
                for entry in all_test_data:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            print(f"\n전체 테스트 데이터셋 저장됨: {all_test_dataset_file}")
        except Exception as e:
            print(f"\n❌ 전체 테스트 데이터셋 저장 실패: {e}")

    return project_counts, len(all_test_data)


def main_test_existing_pipeline():
    """기존 테스트 파일들을 처리하는 파이프라인"""
    print("🧪 기존 테스트 Swift 파일 처리 파이프라인 시작...")

    # 테스트 프로젝트별 디렉토리 생성
    test_projects = get_test_projects()
    if not test_projects:
        print("❌ 테스트 프로젝트를 찾을 수 없습니다!")
        print(f"   {TEST_BASE_DIR} 디렉토리에 프로젝트 폴더를 확인해주세요.")
        return

    print(f"발견된 테스트 프로젝트: {test_projects}")

    # 필요한 디렉토리 생성
    for project in test_projects:
        paths = get_test_project_paths(project)
        for path in paths.values():
            path.mkdir(parents=True, exist_ok=True)

    # 1. 기존 테스트 파일들 발견
    test_tasks = discover_existing_test_files()
    if not test_tasks:
        print("❌ 처리할 Swift 파일을 찾을 수 없습니다!")
        return

    print(f"\n총 {len(test_tasks)}개의 기존 Swift 파일 발견")

    # 2. 병렬 처리로 샘플 생성
    print("\n🔄 기존 Swift 파일들 처리 시작...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        list(tqdm(
            executor.map(process_existing_test_file, test_tasks),
            total=len(test_tasks),
            desc="기존 Swift 파일 처리 중"
        ))

    # 3. 최종 데이터셋 조립
    project_counts, total_count = assemble_test_datasets()

    # 4. 결과 출력
    print(f"\n✅ 기존 테스트 파일 처리 파이프라인 완료!")
    for project, count in project_counts.items():
        print(f"   - {project}: {count}개 데이터")
    print(f"   - 총 테스트 데이터: {total_count}개 생성 완료")

    # 저장된 파일들 정리
    print(f"\n📄 생성된 데이터셋 파일들:")
    for project in test_projects:
        if project_counts.get(project, 0) > 0:
            print(f"   - test_{project}_dataset.jsonl")
    if total_count > 0:
        print(f"   - all_test_dataset.jsonl")


if __name__ == "__main__":
    main_test_existing_pipeline()