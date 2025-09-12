import json
from pathlib import Path
import os

# --- 설정 ---
# 검사할 JSON 파일들이 있는 디렉토리 경로
OUTPUT_DIR = Path("./output")
GENERATED_LABELS_CLAUDE = OUTPUT_DIR / "outputs" / "claude_generated"
GENERATED_LABELS_GEMINI = OUTPUT_DIR / "outputs" / "gemini_generated"


def verify_and_delete_outputs(label_dir: Path, model_name: str) -> int:
    """
    디렉토리를 스캔하여 'identifiers' 리스트가 비어있는 .json 파일을 찾아 즉시 삭제합니다.
    """
    print(f"\n🔍 '{model_name}' 모델 검증 및 삭제 시작: {label_dir}")

    if not label_dir.is_dir():
        print(f"  ⚠️  디렉토리를 찾을 수 없습니다. 건너뜁니다.")
        return 0

    # 삭제 대상이 될 파일들을 먼저 모두 찾습니다.
    files_to_delete = []
    total_positive_files = 0

    for json_file in label_dir.rglob("*_positive.json"):
        total_positive_files += 1
        try:
            content = json_file.read_text(encoding='utf-8')
            data = json.loads(content)

            # 'identifiers' 리스트가 비어있는지 확인
            if "identifiers" in data and isinstance(data["identifiers"], list) and not data["identifiers"]:
                files_to_delete.append(json_file)

        except Exception as e:
            print(f"  [에러] 파일 처리 중 오류 발생 {json_file}: {e}")

    # --- 찾은 파일들을 삭제 ---
    if files_to_delete:
        print(f"  🚨 '{len(files_to_delete)}'개의 문제 파일을 발견하여 삭제합니다:")
        deleted_count = 0
        for json_path in files_to_delete:
            try:
                os.remove(json_path)
                print(f"     - 🗑️ DELETED: {json_path}")
                deleted_count += 1
            except OSError as e:
                print(f"     - ❌ ERROR deleting {json_path}: {e}")
        print(f"\n  ✅ 총 {deleted_count}개의 .json 파일을 삭제했습니다.")
    else:
        print("  ✅ 문제가 발견되지 않았습니다. 모든 파일이 정상입니다.")

    print(f"  📊 이 모델에 대해 총 '{total_positive_files}'개의 positive 샘플 파일을 스캔했습니다.")
    return len(files_to_delete)


def main():
    """메인 실행 함수"""
    print("🚀 문제 있는 output(.json) 파일을 찾아 자동으로 삭제합니다...")
    print("   ('.swift' 코드 파일은 삭제되지 않습니다.)")

    total_problems = 0
    total_problems += verify_and_delete_outputs(GENERATED_LABELS_CLAUDE, "Claude")
    total_problems += verify_and_delete_outputs(GENERATED_LABELS_GEMINI, "Gemini")

    print("\n" + "=" * 50)
    if total_problems > 0:
        print(f"🔴 작업 완료: 총 {total_problems}개의 문제 파일을 삭제했습니다.")
    else:
        print("🟢 작업 완료: 삭제할 파일이 없습니다.")
    print("=" * 50)


if __name__ == "__main__":
    main()