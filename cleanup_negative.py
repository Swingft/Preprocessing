#!/usr/bin/env python3
"""
Negative 샘플 파일들을 삭제하는 별도 스크립트
메인 파이프라인과 분리하여 필요할 때만 실행
"""

import os
from pathlib import Path
import argparse

OUTPUT_DIR = Path("./output")

# 각 생성기별 디렉토리 구조
GENERATED_CODE_CLAUDE = OUTPUT_DIR / "generated_code" / "claude_generated"
GENERATED_CODE_GEMINI = OUTPUT_DIR / "generated_code" / "gemini_generated"
GENERATED_LABELS_CLAUDE = OUTPUT_DIR / "outputs" / "claude_generated"
GENERATED_LABELS_GEMINI = OUTPUT_DIR / "outputs" / "gemini_generated"
GENERATION_PROMPTS_CLAUDE = OUTPUT_DIR / "inputs" / "claude_generated"
GENERATION_PROMPTS_GEMINI = OUTPUT_DIR / "inputs" / "gemini_generated"


def find_negative_files():
    """모든 negative 파일들을 찾아서 반환"""
    all_dirs = [
        GENERATED_CODE_CLAUDE,
        GENERATED_CODE_GEMINI,
        GENERATED_LABELS_CLAUDE,
        GENERATED_LABELS_GEMINI,
        GENERATION_PROMPTS_CLAUDE,
        GENERATION_PROMPTS_GEMINI
    ]

    negative_files = []

    for directory in all_dirs:
        if directory.exists():
            for file_path in directory.rglob("*_negative.*"):
                if file_path.is_file():
                    negative_files.append(file_path)

    return negative_files


def delete_negative_files(dry_run=False):
    """Negative 샘플 파일들을 삭제"""
    negative_files = find_negative_files()

    if not negative_files:
        print("❌ No negative files found.")
        return

    print(f"🔍 Found {len(negative_files)} negative files:")

    # 파일 목록 출력
    for file_path in negative_files:
        print(f"  📄 {file_path}")

    if dry_run:
        print("\n🔍 DRY RUN: Files would be deleted (use --confirm to actually delete)")
        return

    # 실제 삭제
    deleted_count = 0
    failed_count = 0

    print(f"\n🗑️ Deleting {len(negative_files)} files...")

    for file_path in negative_files:
        try:
            file_path.unlink()
            print(f"  ✅ Deleted: {file_path}")
            deleted_count += 1
        except Exception as e:
            print(f"  ❌ Failed to delete {file_path}: {e}")
            failed_count += 1

    print(f"\n📊 Summary:")
    print(f"  ✅ Successfully deleted: {deleted_count} files")
    if failed_count > 0:
        print(f"  ❌ Failed to delete: {failed_count} files")

    print(f"\n🎉 Cleanup completed!")


def delete_by_generator(generator_type, dry_run=False):
    """특정 생성기의 negative 파일들만 삭제"""
    if generator_type not in ["claude", "gemini"]:
        print("❌ Invalid generator type. Use 'claude' or 'gemini'")
        return

    if generator_type == "claude":
        target_dirs = [GENERATED_CODE_CLAUDE, GENERATED_LABELS_CLAUDE, GENERATION_PROMPTS_CLAUDE]
    else:
        target_dirs = [GENERATED_CODE_GEMINI, GENERATED_LABELS_GEMINI, GENERATION_PROMPTS_GEMINI]

    negative_files = []
    for directory in target_dirs:
        if directory.exists():
            for file_path in directory.rglob("*_negative.*"):
                if file_path.is_file():
                    negative_files.append(file_path)

    if not negative_files:
        print(f"❌ No negative files found for {generator_type} generator.")
        return

    print(f"🔍 Found {len(negative_files)} negative files for {generator_type} generator:")

    for file_path in negative_files:
        print(f"  📄 {file_path}")

    if dry_run:
        print(f"\n🔍 DRY RUN: {generator_type} negative files would be deleted (use --confirm to actually delete)")
        return

    # 실제 삭제
    deleted_count = 0
    failed_count = 0

    print(f"\n🗑️ Deleting {len(negative_files)} {generator_type} negative files...")

    for file_path in negative_files:
        try:
            file_path.unlink()
            print(f"  ✅ Deleted: {file_path}")
            deleted_count += 1
        except Exception as e:
            print(f"  ❌ Failed to delete {file_path}: {e}")
            failed_count += 1

    print(f"\n📊 Summary for {generator_type}:")
    print(f"  ✅ Successfully deleted: {deleted_count} files")
    if failed_count > 0:
        print(f"  ❌ Failed to delete: {failed_count} files")


def main():
    parser = argparse.ArgumentParser(description="Delete negative sample files")
    parser.add_argument("--confirm", action="store_true",
                        help="Actually delete files (without this flag, only shows what would be deleted)")
    parser.add_argument("--generator", choices=["claude", "gemini"],
                        help="Delete negative files for specific generator only")

    args = parser.parse_args()

    print("🗑️ Negative Files Cleanup Script")
    print("=" * 50)

    if args.generator:
        print(f"🎯 Target: {args.generator} generator negative files only")
        delete_by_generator(args.generator, dry_run=not args.confirm)
    else:
        print("🎯 Target: All negative files")
        delete_negative_files(dry_run=not args.confirm)


if __name__ == "__main__":
    main()