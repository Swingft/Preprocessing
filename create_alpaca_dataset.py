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
from claude_handler.claude_handler import ClaudeHandler # 코드 생성용
from gemini_handler.gemini_handler import GeminiHandler # 레이블 생성용



ANALYZER_EXECUTABLE = "./SwiftASTAnalyzer/.build/release/SwiftASTAnalyzer"
PATTERNS_FILE = "./patterns.json"
OUTPUT_DIR = Path("./output")
FINAL_DATASET_PATH = OUTPUT_DIR / "json_dataset_by_gemini.jsonl"
GENERATED_CODE_DIR = OUTPUT_DIR / "generated_code"
GENERATED_LABELS_DIR = OUTPUT_DIR / "outputs"
GENERATION_PROMPTS_DIR = OUTPUT_DIR / "inputs"


# --- 2. 헬퍼 함수 (Helper Functions) ---

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


def safe_claude_request(prompt: str, max_retries: int = 3) -> str:
    """Claude API 요청을 안전하게 처리합니다 (코드 생성용)."""
    for attempt in range(max_retries):
        try:
            response = ClaudeHandler.ask(prompt)
            if response and response.strip():
                return response.strip()
        except Exception as e:
            print(f"  ⚠️ Claude request attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    return ""


def safe_gemini_request(prompt: str, max_retries: int = 3) -> str:
    """Gemini API 요청을 안전하게 처리합니다 (레이블 생성용)."""
    for attempt in range(max_retries):
        try:
            # Gemini 핸들러에 맞는 형식으로 변경
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
            print(f"  ⚠️ Gemini request attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    return ""


def process_single_task(task: dict) -> list[dict]:
    """하나의 태스크에 대해 Positive/Negative 샘플 쌍을 생성하고 Alpaca 형식 엔트리를 반환합니다."""
    final_entries = []
    task_type = task['type']
    patterns = task['patterns']

    print(f"  🔄 Processing task: {task['filename']}")

    samples_to_generate = [
        {"is_negative": False, "suffix": "positive"},
        {"is_negative": True, "suffix": "negative"}
    ]

    for sample_info in samples_to_generate:
        is_negative = sample_info['is_negative']
        suffix = sample_info['suffix']
        base_filename = f"{task['filename']}_{suffix}"

        code_path = GENERATED_CODE_DIR / f"{base_filename}.swift"
        label_path = GENERATED_LABELS_DIR / f"{base_filename}.json"
        prompt_path = GENERATION_PROMPTS_DIR / f"{base_filename}.txt"

        # 이어하기 로직
        if code_path.exists() and label_path.exists():
            try:
                swift_code = code_path.read_text(encoding='utf-8')
                json_output_str = label_path.read_text(encoding='utf-8')

                # 기존 파일이 유효한지 확인
                if swift_code.strip() and json_output_str.strip():
                    # JSON 유효성 확인
                    try:
                        json.loads(json_output_str)
                        symbol_info = run_swift_analyzer_on_code(swift_code)
                        if symbol_info:
                            final_entries.append({
                                "instruction": "In the following Swift code, find all identifiers related to sensitive logic. Provide the names and reasoning as a JSON object.",
                                "input": create_alpaca_input(swift_code, symbol_info),
                                "output": json_output_str
                            })
                            continue
                    except json.JSONDecodeError:
                        pass
            except Exception as e:
                print(f"  ⚠️ Error reading existing files for {base_filename}: {e}")

        # 1. 코드 생성 (Claude 사용)
        try:
            prompt = ""
            if task_type.startswith('Pure_nC1'):
                prompt_template = GENERATE_SECURE_SINGLE_CODE_PROMPT if is_negative else GENERATE_SINGLE_CODE_PROMPT
                prompt = prompt_template.format(pattern=patterns[0]['text'])
            elif task_type.startswith('Pure_nC2'):
                prompt_template = GENERATE_SECURE_COMBINED_CODE_PROMPT if is_negative else GENERATE_COMBINED_CODE_PROMPT
                prompt = prompt_template.format(pattern1=patterns[0]['text'], pattern2=patterns[1]['text'])
            elif task_type.startswith('Mixed'):
                prompt_template = GENERATE_SECURE_MIXED_CONTEXT_CODE_PROMPT if is_negative else GENERATE_MIXED_CONTEXT_CODE_PROMPT
                prompt = prompt_template.format(sensitive_pattern=patterns[0]['text'],
                                                nonsensitive_pattern=patterns[1]['text'])

            generated_code = safe_claude_request(prompt)
            if not generated_code:
                print(f"  ❌ Code generation failed for {base_filename}")
                continue

            # Swift 코드 블록 마커 제거
            generated_code = generated_code.removeprefix("```swift").removesuffix("```").strip()
            if not generated_code:
                print(f"  ❌ Empty code after processing for {base_filename}")
                continue

        except Exception as e:
            print(f"  ❌ Code generation error for {base_filename}: {e}")
            continue

        # 2. AST 분석
        try:
            symbol_info_json = run_swift_analyzer_on_code(generated_code)
            if not symbol_info_json:
                print(f"  ❌ AST analysis failed for {base_filename}")
                continue
        except Exception as e:
            print(f"  ❌ AST analysis error for {base_filename}: {e}")
            continue

        # 3. 레이블 및 reasoning 생성/지정 (Gemini 사용)
        json_output_str = ""
        label_prompt_for_file = ""

        try:
            if is_negative:
                pattern_texts = " and ".join([p['text'] for p in patterns])
                reasoning_text = f"This code correctly and securely implements the requested functionality related to '{pattern_texts}'. It follows security best practices. Therefore, no sensitive identifiers were found."
                output_json_obj = {"reasoning": reasoning_text, "identifiers": []}
                json_output_str = json.dumps(output_json_obj, ensure_ascii=False, indent=2)
                label_prompt_for_file = "N/A for negative sample"
            else:
                label_prompt_for_file = f"""You are an expert security code auditor.
Your task is to identify all sensitive identifiers in the provided Swift code and explain your reasoning.
Analyze both the source code and its corresponding AST symbol information.

**Swift Source Code:**
```swift
{generated_code}
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

                # 재시도 로직 (Gemini 사용)
                success = False
                for attempt in range(3):
                    try:
                        raw_response = safe_gemini_request(label_prompt_for_file)
                        if not raw_response:
                            print(f"  ⚠️ Empty response for {base_filename}, attempt {attempt + 1}")
                            continue

                        print(f"  🔍 Raw response length for {base_filename}: {len(raw_response)} chars")

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
                                if isinstance(output_data,
                                              dict) and "reasoning" in output_data and "identifiers" in output_data:
                                    json_output_str = json.dumps(output_data, ensure_ascii=False, indent=2)
                                    success = True
                                    print(f"  ✅ JSON successfully parsed for {base_filename}")
                                    break
                            except json.JSONDecodeError as e:
                                print(f"  ⚠️ JSON candidate failed for {base_filename}: {e}")
                                continue

                        if success:
                            break
                        else:
                            print(f"  ❌ All JSON candidates failed for {base_filename}, attempt {attempt + 1}")
                            print(f"  📄 Response preview: {raw_response[:200]}...")
                            time.sleep(2)

                    except Exception as e:
                        print(f"  ⚠️ Unexpected error for {base_filename}, attempt {attempt + 1}: {e}")
                        time.sleep(2)

                if not success:
                    print(f"  ❌ Label generation failed for {base_filename} after 3 attempts. Skipping.")
                    continue

        except Exception as e:
            print(f"  ❌ Label generation error for {base_filename}: {e}")
            continue

        # 4. 중간 파일 저장 및 Alpaca 엔트리 생성
        try:
            prompt_path.write_text(label_prompt_for_file, encoding='utf-8')
            code_path.write_text(generated_code, encoding='utf-8')
            label_path.write_text(json_output_str, encoding='utf-8')

            alpaca_input = create_alpaca_input(generated_code, symbol_info_json)

            final_entries.append({
                "instruction": "In the following Swift code, find all identifiers related to sensitive logic. Provide the names and reasoning as a JSON object.",
                "input": alpaca_input,
                "output": json_output_str
            })

        except Exception as e:
            print(f"  ❌ File saving error for {base_filename}: {e}")
            continue

    print(f"  ✅ Task {task['filename']} completed: {len(final_entries)} entries")
    return final_entries


def generate_tasks(patterns_by_category: dict) -> list[dict]:
    """nC1, Intra-Category nC2, Cross-Category, Mixed 조합 태스크 목록을 생성합니다."""
    print("🧠 Generating comprehensive task list...")
    tasks = []

    sensitive_patterns = {k: v for k, v in patterns_by_category.items() if not k.startswith("NonSensitive_")}
    nonsensitive_patterns = [p for k, v in patterns_by_category.items() if k.startswith("NonSensitive_") for p in v]

    indexed_patterns = [
        {"id": f"{cat}_{i + 1}", "domain": cat.split('_')[0], "category": cat, "text": p}
        for cat, patterns in sensitive_patterns.items()
        for i, p in enumerate(patterns)
    ]

    # --- 순수(Pure) 태스크 생성 ---
    # nC1
    for p in indexed_patterns:
        tasks.append({"type": "Pure_nC1", "patterns": [p], "filename": p['id']})
    # Intra-Category nC2
    for cat in sensitive_patterns.keys():
        patterns_in_cat = [p for p in indexed_patterns if p['category'] == cat]
        if len(patterns_in_cat) >= 2:
            for p1, p2 in itertools.combinations(patterns_in_cat, 2):
                tasks.append({"type": "Pure_nC2", "patterns": [p1, p2], "filename": f"{p1['id']}_{p2['id']}"})

    # --- 혼합형(Mixed) 태스크 생성 ---
    if nonsensitive_patterns:
        for sens_p in indexed_patterns:
            nonsens_p_text = random.choice(nonsensitive_patterns)
            tasks.append({
                "type": "Mixed",
                "patterns": [sens_p, {"text": nonsens_p_text}],
                "filename": f"Mixed_{sens_p['id']}"
            })

    unique_tasks = {task['filename']: task for task in tasks}.values()
    print(f"✅ Task list generated. Total unique tasks: {len(unique_tasks)} (each will create a positive/negative pair)")
    return list(unique_tasks)


# --- 3. 메인 파이프라인 (Main Pipeline) ---
def main_pipeline():
    """최종 데이터셋 생성 파이프라인 (Claude: 코드 생성, Gemini: 레이블 생성)"""
    print("🚀 Starting Alpaca dataset generation pipeline (Claude + Gemini)...")
    print("  📝 Claude: Code generation")
    print("  🏷️  Gemini: Label generation")

    GENERATED_CODE_DIR.mkdir(parents=True, exist_ok=True)
    GENERATED_LABELS_DIR.mkdir(parents=True, exist_ok=True)
    GENERATION_PROMPTS_DIR.mkdir(parents=True, exist_ok=True)

    # 패턴 로드
    try:
        with open(PATTERNS_FILE, "r", encoding="utf-8") as f:
            patterns_by_category = json.load(f)
    except Exception as e:
        print(f"❌ Failed to load patterns file: {e}")
        return

    tasks = generate_tasks(patterns_by_category)
    final_dataset = []

    for i, task in enumerate(tqdm(tasks, desc="Processing all tasks")):
        try:
            entries = process_single_task(task)
            if entries:
                final_dataset.extend(entries)
        except Exception as exc:
            print(f"  ❌ Task {task['filename']} generated an exception: {exc}")
            import traceback
            traceback.print_exc()

    # 최종 데이터셋 파일 저장
    try:
        with open(FINAL_DATASET_PATH, "w", encoding="utf-8") as f:
            for entry in final_dataset:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        print(f"\n✅ Pipeline finished. Total {len(final_dataset)} entries processed and saved to {FINAL_DATASET_PATH}")

    except Exception as e:
        print(f"❌ Failed to save final dataset: {e}")


if __name__ == "__main__":
    main_pipeline()