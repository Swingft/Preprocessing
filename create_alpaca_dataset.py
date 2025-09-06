import os
import json
import re
import hashlib
import subprocess
import tempfile
from pathlib import Path
from tqdm import tqdm
import itertools
from prompts import GENERATE_SINGLE_CODE_PROMPT, GENERATE_COMBINED_CODE_PROMPT, GENERATE_LABELS_PROMPT
from claude_handler.claude_handler import ClaudeHandler


ANALYZER_EXECUTABLE = "./SwiftASTAnalyzer/.build/release/SwiftASTAnalyzer"
PATTERNS_FILE = "./patterns.json"
OUTPUT_DIR = Path("./output")
FINAL_DATASET_PATH = OUTPUT_DIR / "alpaca_dataset.jsonl"
GENERATED_CODE_DIR = OUTPUT_DIR / "generated_code"

GENERATED_LABELS_DIR = OUTPUT_DIR / "outputs"
GENERATION_PROMPTS_DIR = OUTPUT_DIR / "inputs"


def run_swift_analyzer_on_code(swift_code: str) -> str | None:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_file_path = Path(temp_dir) / "temp.swift"
        temp_file_path.write_text(swift_code, encoding='utf-8')
        command = [ANALYZER_EXECUTABLE, str(temp_file_path.absolute())]
        try:
            process = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8')
            return process.stdout
        except subprocess.CalledProcessError as e:
            print(f"Error analyzing swift code: {e}\nSTDERR: {e.stderr}")
            return None


def create_alpaca_input(swift_code: str, symbol_info_json: str) -> str:
    try:
        symbol_info_pretty = json.dumps(json.loads(symbol_info_json), indent=2)
    except json.JSONDecodeError:
        symbol_info_pretty = symbol_info_json
    return f"**Swift Source Code:**\n```swift\n{swift_code}\n```\n\n**AST Symbol Information (JSON):**\n```\n{symbol_info_pretty}\n```"


def process_and_save_entry(base_filename: str, generated_swift_code: str) -> dict | None:
    code_path = GENERATED_CODE_DIR / f"{base_filename}.swift"
    label_path = GENERATED_LABELS_DIR / f"{base_filename}.json"
    prompt_path = GENERATION_PROMPTS_DIR / f"{base_filename}.txt"

    # AST 분석
    symbol_info_json_for_label = run_swift_analyzer_on_code(generated_swift_code)
    if not symbol_info_json_for_label:
        print("  ⚠️ AST analysis failed for labeling. Skipping.")
        return None

    # 레이블 생성용 프롬프트 만들기 및 저장
    label_prompt = GENERATE_LABELS_PROMPT.format(swift_code=generated_swift_code,
                                                 symbol_info_json=symbol_info_json_for_label)
    print("  💾 Saving generation prompt locally...")
    prompt_path.write_text(label_prompt, encoding='utf-8')

    # Claude API 호출하여 레이블 생성
    json_labels_str = ClaudeHandler.ask(label_prompt).strip().removeprefix("```json").removesuffix("```").strip()

    # 중간 파일(코드, 레이블) 저장
    print("  💾 Saving intermediate code and label files locally...")
    code_path.write_text(generated_swift_code, encoding='utf-8')
    label_path.write_text(json_labels_str, encoding='utf-8')

    # 최종 데이터셋 엔트리 생성
    try:
        labels = json.loads(json_labels_str)
        if not isinstance(labels, list): raise ValueError("Label is not a list.")
    except (json.JSONDecodeError, ValueError) as e:
        print(f"  ⚠️ Label parsing failed: {e}. Skipping entry.")
        return None

    alpaca_input = create_alpaca_input(generated_swift_code, symbol_info_json_for_label)
    alpaca_output = json.dumps(labels, ensure_ascii=False)

    return {
        "instruction": "In the following Swift code, find all identifiers related to sensitive logic (including Privacy, Security, Financial, Permissions, Networking, and Device ID). Provide the names of the found identifiers as a JSON list.",
        "input": alpaca_input,
        "output": alpaca_output
    }


def main_pipeline():
    print("🚀 Starting Alpaca dataset generation pipeline (nC1 and nC2)...")
    GENERATED_CODE_DIR.mkdir(parents=True, exist_ok=True)
    GENERATED_LABELS_DIR.mkdir(parents=True, exist_ok=True)
    GENERATION_PROMPTS_DIR.mkdir(parents=True, exist_ok=True)

    with open(PATTERNS_FILE, "r", encoding="utf-8") as f:
        patterns_by_category = json.load(f)

    indexed_patterns = [{"id": f"{cat}_{i + 1}", "category": cat, "text": p} for cat, patterns in
                        patterns_by_category.items() for i, p in enumerate(patterns)]

    tasks = []
    for p in indexed_patterns:
        tasks.append({"type": "nC1", "patterns": [p], "filename": p['id']})
    combination_pairs = [(p1, p2) for p1, p2 in itertools.combinations(indexed_patterns, 2) if
                         p1["category"] != p2["category"]]
    for p1, p2 in combination_pairs:
        tasks.append({"type": "nC2", "patterns": [p1, p2], "filename": f"{p1['id']}_{p2['id']}"})

    final_dataset = []
    for task in tqdm(tasks, desc="Processing all tasks"):
        base_filename = task['filename']
        code_path = GENERATED_CODE_DIR / f"{base_filename}.swift"
        label_path = GENERATED_LABELS_DIR / f"{base_filename}.json"

        if code_path.exists() and label_path.exists():
            print(f"\n--- Loading from existing files: {base_filename} ---")
            try:
                swift_code = code_path.read_text(encoding='utf-8')
                json_labels_str = label_path.read_text(encoding='utf-8')
                symbol_info = run_swift_analyzer_on_code(swift_code)
                if symbol_info:
                    labels = json.loads(json_labels_str)
                    final_dataset.append({
                        "instruction": "In the following Swift code, find all identifiers related to sensitive logic (including Privacy, Security, Financial, Permissions, Networking, and Device ID). Provide the names of the found identifiers as a JSON list.",
                        "input": create_alpaca_input(swift_code, symbol_info),
                        "output": json.dumps(labels, ensure_ascii=False)
                    })
                continue
            except Exception as e:
                print(f"  ⚠️ Failed to load existing files for '{base_filename}': {e}. Regenerating.")

        print(f"\n--- Generating for: {base_filename} ---")
        try:
            if task['type'] == 'nC1':
                p = task['patterns'][0]
                prompt = GENERATE_SINGLE_CODE_PROMPT.format(pattern=p['text'])
            else:  # nC2
                p1, p2 = task['patterns']
                prompt = GENERATE_COMBINED_CODE_PROMPT.format(pattern1=p1['text'], pattern2=p2['text'])

            code = ClaudeHandler.ask(prompt).strip().removeprefix("```swift").removesuffix("```").strip()
            if code:
                entry = process_and_save_entry(base_filename, code)
                if entry:
                    final_dataset.append(entry)
        except Exception as e:
            print(f"  ❌ An unexpected error occurred for '{base_filename}': {e}")

    with open(FINAL_DATASET_PATH, "w", encoding="utf-8") as f:
        for entry in final_dataset:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"\n✅ Pipeline finished. Total {len(final_dataset)} entries processed and saved to {FINAL_DATASET_PATH}")


if __name__ == "__main__":
    main_pipeline()