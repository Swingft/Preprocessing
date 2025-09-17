#!/usr/bin/env python3
"""
독립적인 데이터셋 통계 분석 스크립트
JSONL 형태의 Alpaca 데이터셋을 분석하여 identifiers 분포와 통계 정보 제공
"""

import json
import argparse
import statistics
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Any, Optional
import sys


def load_jsonl_dataset(file_path: Path) -> List[Dict[str, Any]]:
    """JSONL 파일을 로드하여 리스트로 반환"""
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return []

    dataset = []
    error_count = 0

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line:
                    try:
                        entry = json.loads(line)
                        dataset.append(entry)
                    except json.JSONDecodeError as e:
                        error_count += 1
                        if error_count <= 5:  # 처음 5개 에러만 출력
                            print(f"⚠️ JSON decode error at line {line_num}: {e}")
                        elif error_count == 6:
                            print(f"⚠️ ... (더 많은 JSON 에러가 있습니다)")
    except Exception as e:
        print(f"❌ Error reading file {file_path}: {e}")
        return []

    if error_count > 0:
        print(f"⚠️ Total JSON decode errors: {error_count}")

    print(f"✅ Loaded {len(dataset)} valid entries from {file_path.name}")
    return dataset


def extract_output_data(entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """출력 JSON에서 reasoning과 identifiers 추출"""
    try:
        output_str = entry.get('output', '').strip()
        if not output_str:
            return None

        output_data = json.loads(output_str)
        if not isinstance(output_data, dict):
            return None

        if 'reasoning' not in output_data or 'identifiers' not in output_data:
            return None

        return {
            'reasoning': output_data['reasoning'],
            'identifiers': output_data['identifiers'],
            'raw_output': output_str
        }
    except (json.JSONDecodeError, TypeError, KeyError):
        return None


def categorize_sample(identifiers: List[str]) -> str:
    """샘플을 카테고리로 분류"""
    if not isinstance(identifiers, list):
        return "invalid"

    if len(identifiers) == 0:
        return "secure"  # 빈 리스트 = 보안이 잘 된 코드
    else:
        return "vulnerable"  # 비어있지 않은 리스트 = 취약한 코드


def analyze_dataset_statistics(dataset: List[Dict[str, Any]], dataset_name: str = "Dataset") -> Dict[str, Any]:
    """데이터셋의 상세 통계 분석"""
    print(f"\n📊 {dataset_name} Analysis")
    print("=" * 70)

    stats = {
        'dataset_name': dataset_name,
        'total_entries': len(dataset),
        'valid_outputs': 0,
        'invalid_outputs': 0,
        'secure_samples': 0,  # 빈 identifiers
        'vulnerable_samples': 0,  # 비어있지 않은 identifiers
        'identifier_counts': Counter(),  # 개수별 분포
        'all_identifiers': [],
        'unique_identifiers': set(),
        'reasoning_lengths': [],
        'sample_categories': defaultdict(list),
        'identifier_frequency': Counter(),
    }

    # 각 엔트리 분석
    for i, entry in enumerate(dataset):
        output_data = extract_output_data(entry)

        if output_data is None:
            stats['invalid_outputs'] += 1
            continue

        stats['valid_outputs'] += 1

        identifiers = output_data['identifiers']
        reasoning = output_data['reasoning']

        # 샘플 분류
        category = categorize_sample(identifiers)
        stats['sample_categories'][category].append(i)

        # identifiers 분석
        if isinstance(identifiers, list):
            if len(identifiers) == 0:
                stats['secure_samples'] += 1
            else:
                stats['vulnerable_samples'] += 1
                stats['identifier_counts'][len(identifiers)] += 1

                # 개별 identifier 분석
                for identifier in identifiers:
                    if isinstance(identifier, str):
                        stats['all_identifiers'].append(identifier)
                        stats['unique_identifiers'].add(identifier)
                        stats['identifier_frequency'][identifier] += 1

        # reasoning 길이 분석
        if isinstance(reasoning, str):
            stats['reasoning_lengths'].append(len(reasoning))

    # 결과 출력
    print_basic_statistics(stats)
    print_identifier_analysis(stats)
    print_vulnerability_analysis(stats)
    print_reasoning_analysis(stats)

    return stats


def print_basic_statistics(stats: Dict[str, Any]):
    """기본 통계 출력"""
    print(f"📋 Basic Statistics:")
    print(f"  Total entries: {stats['total_entries']:,}")
    print(f"  Valid outputs: {stats['valid_outputs']:,}")
    print(f"  Invalid outputs: {stats['invalid_outputs']:,}")

    if stats['valid_outputs'] > 0:
        valid_pct = (stats['valid_outputs'] / stats['total_entries']) * 100
        print(f"  Success rate: {valid_pct:.1f}%")


def print_identifier_analysis(stats: Dict[str, Any]):
    """Identifier 분석 출력"""
    if stats['valid_outputs'] == 0:
        return

    secure_pct = (stats['secure_samples'] / stats['valid_outputs']) * 100
    vulnerable_pct = (stats['vulnerable_samples'] / stats['valid_outputs']) * 100

    print(f"\n🔍 Sample Classification:")
    print(f"  Secure samples (empty identifiers): {stats['secure_samples']:,} ({secure_pct:.1f}%)")
    print(f"  Vulnerable samples (non-empty identifiers): {stats['vulnerable_samples']:,} ({vulnerable_pct:.1f}%)")

    if stats['vulnerable_samples'] > 0:
        print(f"\n📈 Identifier Count Distribution (Vulnerable Samples Only):")
        for count in sorted(stats['identifier_counts'].keys()):
            freq = stats['identifier_counts'][count]
            pct = (freq / stats['vulnerable_samples']) * 100
            print(f"  {count} identifiers: {freq:,} samples ({pct:.1f}%)")

        # 통계값 계산
        all_counts = []
        for count, freq in stats['identifier_counts'].items():
            all_counts.extend([count] * freq)

        if all_counts:
            print(f"\n📊 Identifier Count Statistics (Vulnerable Samples):")
            print(f"  Min identifiers per sample: {min(all_counts)}")
            print(f"  Max identifiers per sample: {max(all_counts)}")
            print(f"  Mean identifiers per sample: {statistics.mean(all_counts):.1f}")
            print(f"  Median identifiers per sample: {statistics.median(all_counts):.1f}")


def print_vulnerability_analysis(stats: Dict[str, Any]):
    """취약점 분석 출력"""
    if not stats['all_identifiers']:
        return

    print(f"\n🏆 Most Frequent Vulnerability Identifiers:")
    for identifier, count in stats['identifier_frequency'].most_common(15):
        pct = (count / len(stats['all_identifiers'])) * 100
        print(f"  '{identifier}': {count:,} times ({pct:.1f}%)")

    print(f"\n📊 Identifier Diversity:")
    print(f"  Unique identifiers: {len(stats['unique_identifiers']):,}")
    print(f"  Total identifier instances: {len(stats['all_identifiers']):,}")

    if len(stats['unique_identifiers']) > 0:
        avg_frequency = len(stats['all_identifiers']) / len(stats['unique_identifiers'])
        print(f"  Average frequency per unique identifier: {avg_frequency:.1f}")


def print_reasoning_analysis(stats: Dict[str, Any]):
    """Reasoning 분석 출력"""
    if not stats['reasoning_lengths']:
        return

    print(f"\n📝 Reasoning Text Analysis:")
    print(f"  Min length: {min(stats['reasoning_lengths']):,} characters")
    print(f"  Max length: {max(stats['reasoning_lengths']):,} characters")
    print(f"  Mean length: {statistics.mean(stats['reasoning_lengths']):.1f} characters")
    print(f"  Median length: {statistics.median(stats['reasoning_lengths']):.1f} characters")

    # 길이 분포
    length_ranges = [
        (0, 100, "Very Short"),
        (101, 200, "Short"),
        (201, 400, "Medium"),
        (401, 600, "Long"),
        (601, float('inf'), "Very Long")
    ]

    print(f"\n📏 Reasoning Length Distribution:")
    for min_len, max_len, label in length_ranges:
        count = sum(1 for length in stats['reasoning_lengths']
                    if min_len <= length <= max_len)
        if count > 0:
            pct = (count / len(stats['reasoning_lengths'])) * 100
            range_str = f"{min_len}-{max_len}" if max_len != float('inf') else f"{min_len}+"
            print(f"  {label} ({range_str} chars): {count:,} samples ({pct:.1f}%)")


def compare_datasets(all_stats: List[Dict[str, Any]]):
    """여러 데이터셋 비교"""
    if len(all_stats) <= 1:
        return

    print(f"\n🔄 Dataset Comparison")
    print("=" * 70)

    # 헤더 출력
    print(f"{'Dataset':<20} {'Total':<8} {'Valid':<8} {'Secure':<8} {'Vulnerable':<10} {'Unique IDs':<10}")
    print("-" * 70)

    for stats in all_stats:
        name = stats['dataset_name'][:18]  # 이름 길이 제한
        total = stats['total_entries']
        valid = stats['valid_outputs']
        secure = stats['secure_samples']
        vulnerable = stats['vulnerable_samples']
        unique_ids = len(stats['unique_identifiers'])

        print(f"{name:<20} {total:<8,} {valid:<8,} {secure:<8,} {vulnerable:<10,} {unique_ids:<10,}")

    # 비율 비교
    print(f"\n📊 Percentage Comparison:")
    print(f"{'Dataset':<20} {'Success%':<10} {'Secure%':<10} {'Vulnerable%':<12}")
    print("-" * 60)

    for stats in all_stats:
        name = stats['dataset_name'][:18]
        if stats['total_entries'] > 0:
            success_pct = (stats['valid_outputs'] / stats['total_entries']) * 100
        else:
            success_pct = 0

        if stats['valid_outputs'] > 0:
            secure_pct = (stats['secure_samples'] / stats['valid_outputs']) * 100
            vulnerable_pct = (stats['vulnerable_samples'] / stats['valid_outputs']) * 100
        else:
            secure_pct = vulnerable_pct = 0

        print(f"{name:<20} {success_pct:<10.1f} {secure_pct:<10.1f} {vulnerable_pct:<12.1f}")


def save_detailed_report(all_stats: List[Dict[str, Any]], output_file: Path):
    """상세 보고서를 JSON 파일로 저장"""
    try:
        # set을 list로 변환하여 JSON 직렬화 가능하게 만듦
        serializable_stats = []
        for stats in all_stats:
            serializable = dict(stats)
            serializable['unique_identifiers'] = list(stats['unique_identifiers'])
            serializable['sample_categories'] = dict(stats['sample_categories'])
            serializable_stats.append(serializable)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(serializable_stats, f, ensure_ascii=False, indent=2)

        print(f"💾 Detailed report saved to: {output_file}")
    except Exception as e:
        print(f"❌ Failed to save report: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze Alpaca dataset statistics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python analyze_dataset.py                                    # Analyze output/combined_dataset.jsonl (default)
  python analyze_dataset.py dataset.jsonl                      # Analyze specific file
  python analyze_dataset.py dataset1.jsonl dataset2.jsonl --compare
  python analyze_dataset.py --all --compare                    # Analyze all datasets and compare
  python analyze_dataset.py --save-report stats_report.json   # Save report for default dataset
        """
    )

    parser.add_argument("files", nargs="*",
                        help="JSONL dataset files to analyze (default: output/combined_dataset.jsonl)")
    parser.add_argument("--all", action="store_true",
                        help="Analyze all available datasets (claude_only, gemini_only, combined)")
    parser.add_argument("--compare", action="store_true",
                        help="Compare multiple datasets (if more than one file provided)")
    parser.add_argument("--save-report", type=str, metavar="FILE",
                        help="Save detailed statistics report to JSON file")
    parser.add_argument("--quiet", action="store_true",
                        help="Only show summary without detailed analysis")

    args = parser.parse_args()

    print("📊 Dataset Statistics Analyzer")
    print("=" * 50)

    # 분석할 파일 목록 결정
    files_to_analyze = []

    if args.all:
        # 모든 데이터셋 분석
        potential_files = [
            "output/claude_only_dataset.jsonl",
            "output/gemini_only_dataset.jsonl",
            "output/combined_dataset.jsonl"
        ]
        for file_path_str in potential_files:
            file_path = Path(file_path_str)
            if file_path.exists():
                files_to_analyze.append(file_path_str)

        if not files_to_analyze:
            print("❌ No dataset files found in output directory")
            sys.exit(1)

        # --all 옵션 사용 시 자동으로 비교 모드 활성화
        args.compare = True

    elif args.files:
        # 사용자가 지정한 파일들
        files_to_analyze = args.files
    else:
        # 기본값: combined_dataset.jsonl
        default_file = "output/combined_dataset.jsonl"
        if Path(default_file).exists():
            files_to_analyze = [default_file]
            print(f"📁 Using default dataset: {default_file}")
        else:
            print(f"❌ Default dataset not found: {default_file}")
            print("💡 Available options:")
            print("   --all                    # Analyze all available datasets")
            print("   <filename>               # Specify a dataset file")
            sys.exit(1)

    all_stats = []

    for file_path_str in files_to_analyze:
        file_path = Path(file_path_str)
        if not file_path.exists():
            print(f"❌ File not found: {file_path}")
            continue

        dataset = load_jsonl_dataset(file_path)
        if not dataset:
            continue

        dataset_name = file_path.stem
        if not args.quiet:
            stats = analyze_dataset_statistics(dataset, dataset_name)
        else:
            # 간단한 통계만 계산
            stats = {'dataset_name': dataset_name, 'total_entries': len(dataset)}

        all_stats.append(stats)

    # 여러 데이터셋 비교
    if args.compare and len(all_stats) > 1:
        compare_datasets(all_stats)

    # 보고서 저장
    if args.save_report:
        save_detailed_report(all_stats, Path(args.save_report))

    if not all_stats:
        print("❌ No valid datasets found to analyze")
        sys.exit(1)

    print(f"\n✅ Analysis completed for {len(all_stats)} dataset(s)")


if __name__ == "__main__":
    main()