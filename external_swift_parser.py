import os
import requests
import pandas as pd
import json
from github import Github
from itertools import cycle
from dotenv import load_dotenv
from claude_handler import ClaudeHandler
from prompt_templates import create_swift_analysis_prompt
from datetime import datetime

load_dotenv()

TOKENS = [
    os.getenv("GITHUB_TOKEN_DH"),
    os.getenv("GITHUB_TOKEN_GN"),
    os.getenv("GITHUB_TOKEN_HJ"),
    os.getenv("GITHUB_TOKEN_SH"),
    os.getenv("GITHUB_TOKEN_SI")
]

if not all(TOKENS):
    raise ValueError("모든 토큰이 .env 파일에 정의되어 있어야 합니다.")

token_cycle = cycle(TOKENS)

csv_file = "swift_spm_networking_repos.csv"
df = pd.read_csv(csv_file)

df_sorted = df.sort_values(['stars', 'year'], ascending=[False, False])
repo_names = df_sorted['repo'].tolist()[1:2]

print(f"총 {len(repo_names)}개 리포지토리 (stars 높은 순, 년도 최신 순으로 정렬됨)")
print(f"차상위 1개: {repo_names[1:2]}")


def get_github_instance():
    return Github(next(token_cycle))


def should_exclude_path(path):
    """제외할 경로 또는 파일인지 확인"""
    path_parts = path.split('/')
    lower_path = path.lower()

    # 1. SPM 관련 파일/디렉토리
    if '.build' in path_parts:
        return True
    if lower_path.endswith('package.swift'):
        return True
    if lower_path.endswith('package.resolved'):
        return True

    # 2. 테스트 관련 디렉토리
    test_dirs = ['tests', 'test', 'testing', 'unitTests', 'uitests', 'integrationtests']
    if any(test_dir in [part.lower() for part in path_parts] for test_dir in test_dirs):
        return True

    # 3. 예제/데모/샘플 디렉토리
    example_dirs = ['examples', 'example', 'demo', 'demos', 'sample', 'samples', 'playground', 'playgrounds']
    if any(example_dir in [part.lower() for part in path_parts] for example_dir in example_dirs):
        return True

    # 4. 문서 관련 디렉토리
    doc_dirs = ['docs', 'documentation', 'doc']
    if any(doc_dir in [part.lower() for part in path_parts] for doc_dir in doc_dirs):
        return True

    # 5. 빌드/임시 파일들
    build_dirs = ['build', 'deriveddata', '.swiftpm', 'xcuserdata']
    if any(build_dir in [part.lower() for part in path_parts] for build_dir in build_dirs):
        return True

    # 6. 의존성 관리 디렉토리
    dependency_dirs = ['vendor', 'third_party', 'thirdparty', 'external', 'carthage', 'pods', 'node_modules']
    if any(dep_dir in [part.lower() for part in path_parts] for dep_dir in dependency_dirs):
        return True

    # 7. 툴링/스크립트 디렉토리
    tool_dirs = ['scripts', 'tools', 'fastlane', '.github', '.gitlab']
    if any(tool_dir in [part.lower() for part in path_parts] for tool_dir in tool_dirs):
        return True

    # 8. 특정 파일 확장자 제외
    excluded_extensions = ['.md', '.txt', '.json', '.yml', '.yaml', '.xml', '.plist', '.sh', '.rb', '.py']
    if any(lower_path.endswith(ext) for ext in excluded_extensions):
        return True

    # 9. 숨김 디렉토리/파일
    if any(part.startswith('.') and part not in ['.swift-version'] for part in path_parts):
        return True

    return False


def find_swift_files_in_directory(repo, directory_path, branch_name):
    """디렉토리에서 Swift 파일을 재귀적으로 찾기"""
    swift_files = []

    try:
        contents = repo.get_contents(directory_path, ref=branch_name)

        for content in contents:
            if should_exclude_path(content.path):
                print(f"    제외: {content.path}")
                continue

            if content.type == 'dir':
                subfolder_files = find_swift_files_in_directory(repo, content.path, branch_name)
                swift_files.extend(subfolder_files)
            elif content.type == 'file' and content.path.endswith('.swift'):
                swift_files.append(content.path)

    except Exception as e:
        print(f"    디렉토리 '{directory_path}' 접근 실패: {e}")

    return swift_files


def get_all_swift_files(repo):
    """리포지토리에서 모든 Swift 파일 경로 반환"""
    swift_files = []
    branch_name = None

    try:
        branch_name = repo.default_branch
        print(f"  기본 브랜치 '{branch_name}' 사용")
        swift_files = find_swift_files_in_directory(repo, "", branch_name)

    except Exception as e:
        print(f"  기본 브랜치 실패: {e}")

        alternative_branches = ['main', 'master']
        for branch in alternative_branches:
            try:
                print(f"  브랜치 '{branch}' 시도...")
                swift_files = find_swift_files_in_directory(repo, "", branch)
                branch_name = branch
                print(f"  브랜치 '{branch}' 성공!")
                break
            except Exception as branch_error:
                print(f"  브랜치 '{branch}' 실패: {branch_error}")
                continue

    print(f"  발견된 Swift 파일: {len(swift_files)}개")
    return swift_files, branch_name


def save_analysis_result_locally(repo_name, file_path, swift_code_generated, json_label,
                                 local_analysis_dir="./analysis_results"):
    """Claude 분석 결과를 로컬에 저장"""
    try:
        # 리포지토리별 디렉토리 생성
        repo_dir = os.path.join(local_analysis_dir, repo_name.replace('/', '_'))
        os.makedirs(repo_dir, exist_ok=True)

        # 파일 경로에서 디렉토리 구조 유지
        file_dir = os.path.dirname(file_path)
        if file_dir:
            full_dir = os.path.join(repo_dir, file_dir)
            os.makedirs(full_dir, exist_ok=True)

        # 파일명에서 확장자 제거하고 분석 결과 접미사 추가
        base_filename = os.path.splitext(os.path.basename(file_path))[0]

        # 1. 생성된 Swift 코드 저장
        swift_analysis_path = os.path.join(repo_dir, file_dir, f"{base_filename}_analysis.swift")
        with open(swift_analysis_path, 'w', encoding='utf-8') as f:
            f.write(f"// Claude 분석 결과 - {file_path}\n")
            f.write(f"// Repository: {repo_name}\n")
            f.write(f"// Generated at: {datetime.now().isoformat()}\n\n")
            f.write(swift_code_generated)

        # 2. JSON 라벨 저장
        json_analysis_path = os.path.join(repo_dir, file_dir, f"{base_filename}_labels.json")
        with open(json_analysis_path, 'w', encoding='utf-8') as f:
            # JSON 문자열을 파싱해서 예쁘게 저장
            try:
                json_data = json.loads(json_label)
                # 메타데이터 추가
                json_data['_metadata'] = {
                    'original_file': file_path,
                    'repository': repo_name,
                    'generated_at': datetime.now().isoformat()
                }
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            except json.JSONDecodeError:
                # JSON 파싱 실패시 원본 문자열 저장
                fallback_data = {
                    'raw_response': json_label,
                    '_metadata': {
                        'original_file': file_path,
                        'repository': repo_name,
                        'generated_at': datetime.now().isoformat(),
                        'error': 'JSON parsing failed'
                    }
                }
                json.dump(fallback_data, f, indent=2, ensure_ascii=False)

        # 3. 통합 분석 결과 저장 (Swift + JSON)
        combined_analysis_path = os.path.join(repo_dir, file_dir, f"{base_filename}_combined_analysis.md")
        with open(combined_analysis_path, 'w', encoding='utf-8') as f:
            f.write(f"# Claude 분석 결과\n\n")
            f.write(f"- **파일**: {file_path}\n")
            f.write(f"- **리포지토리**: {repo_name}\n")
            f.write(f"- **생성 시간**: {datetime.now().isoformat()}\n\n")
            f.write(f"## 생성된 Swift 코드\n\n```swift\n{swift_code_generated}\n```\n\n")
            f.write(f"## JSON 라벨\n\n```json\n{json_label}\n```\n")

        print(f"      💾 로컬 저장 완료:")
        print(f"        - Swift: {swift_analysis_path}")
        print(f"        - JSON: {json_analysis_path}")
        print(f"        - Combined: {combined_analysis_path}")

        return True

    except Exception as e:
        print(f"      ❌ 로컬 저장 실패: {e}")
        return False


def download_and_analyze_swift_file(repo_name, file_path, token, branch_name, save_directory="./swift_files"):
    """Swift 파일을 다운로드하고 Claude로 분석"""
    raw_url = f"https://raw.githubusercontent.com/{repo_name}/{branch_name}/{file_path}"
    headers = {"Authorization": f"token {token}"}

    try:
        # 1. Swift 파일 다운로드
        response = requests.get(raw_url, headers=headers)
        response.raise_for_status()
        swift_code = response.text

        # 2. 로컬에 원본 파일 저장
        local_file_path = os.path.join(save_directory, repo_name.replace('/', '_'), file_path)
        os.makedirs(os.path.dirname(local_file_path), exist_ok=True)

        with open(local_file_path, 'w', encoding='utf-8') as f:
            f.write(swift_code)

        # 3. 프롬프트 생성 및 Claude 분석
        module_name = repo_name.split('/')[-1]
        prompt = create_swift_analysis_prompt(module_name, file_path, repo_name, swift_code)

        print(f"      🔹 Claude 종합 분석 중: {file_path}")

        claude_reply = ClaudeHandler.ask(prompt)
        swift_code_generated, json_label = parse_claude_response(claude_reply)

        # 4. Google Drive에 저장 (기존 기능)
        ClaudeHandler.save_and_upload_analysis_result(swift_code_generated, json_label, repo_name, file_path)

        # 5. 로컬에 분석 결과 저장 (신규 기능)
        save_analysis_result_locally(repo_name, file_path, swift_code_generated, json_label)

        print(f"      ✅ Claude 분석 완료: {file_path}")
        return True

    except Exception as e:
        print(f"      ❌ 파일 처리 실패 ({file_path}): {e}")
        return False


def parse_claude_response(response):
    """Claude 응답에서 Swift 코드와 JSON을 분리"""
    try:
        # Swift 코드 추출
        swift_start = response.find("// === GENERATED_SWIFT_CODE ===")
        swift_end = response.find("```json")

        if swift_start != -1 and swift_end != -1:
            swift_code = response[swift_start:swift_end].replace("// === GENERATED_SWIFT_CODE ===", "").strip()
            swift_code = swift_code.replace("```swift", "").replace("```", "").strip()
        else:
            swift_code = "// Swift 코드 파싱 실패"

        # JSON 추출
        json_start = response.find("// === JSON_LABEL ===")
        json_end = response.rfind("```")

        if json_start != -1:
            json_content = response[json_start:json_end if json_end != -1 else len(response)]
            json_content = json_content.replace("// === JSON_LABEL ===", "").strip()
            json_content = json_content.replace("```json", "").replace("```", "").strip()
        else:
            json_content = '{"error": "JSON 파싱 실패"}'

        return swift_code, json_content

    except Exception as e:
        print(f"      ⚠️ 응답 파싱 실패: {e}")
        return "// 파싱 실패", '{"error": "파싱 실패"}'


def create_analysis_summary(successful_repos, local_analysis_dir="./analysis_results"):
    """분석 결과 요약 파일 생성"""
    try:
        summary_path = os.path.join(local_analysis_dir, "analysis_summary.md")

        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write("# Swift 리포지토리 분석 요약\n\n")
            f.write(f"- **분석 실행 시간**: {datetime.now().isoformat()}\n")
            f.write(f"- **총 분석 리포지토리**: {len(successful_repos)}개\n\n")

            for repo in successful_repos:
                f.write(f"## {repo['name']}\n\n")
                f.write(f"- **브랜치**: {repo['branch']}\n")
                f.write(f"- **발견된 Swift 파일**: {repo['count']}개\n")
                f.write(f"- **분석된 파일**: {repo['analyzed_count']}개\n\n")

            f.write("## 디렉토리 구조\n\n")
            f.write("```\n")
            f.write("analysis_results/\n")
            f.write("├── analysis_summary.md (이 파일)\n")
            for repo in successful_repos:
                repo_dir = repo['name'].replace('/', '_')
                f.write(f"├── {repo_dir}/\n")
                f.write(f"│   ├── *_analysis.swift (생성된 Swift 코드)\n")
                f.write(f"│   ├── *_labels.json (JSON 라벨)\n")
                f.write(f"│   └── *_combined_analysis.md (통합 분석)\n")
            f.write("```\n")

        print(f"📋 분석 요약 파일 생성: {summary_path}")
        return True

    except Exception as e:
        print(f"❌ 요약 파일 생성 실패: {e}")
        return False


def main():
    total_swift_files = 0
    successful_repos = []
    failed_repos = []
    total_analyzed_files = 0

    print(f"🚀 Swift 파일 수집 및 Claude 분석 시작!")
    print(f"총 {len(repo_names)}개 리포지토리 처리 시작...")
    print("🤖 각 Swift 파일은 Claude로 Public API 분석됩니다.")
    print("💾 분석 결과는 Google Drive와 로컬에 모두 저장됩니다.\n")

    for idx, repo_name in enumerate(repo_names, 1):
        print(f"[{idx}/{len(repo_names)}] 처리 중: {repo_name}")

        try:
            github_client = get_github_instance()
            repository = github_client.get_repo(repo_name)
            swift_file_list, used_branch = get_all_swift_files(repository)

            if swift_file_list:
                total_swift_files += len(swift_file_list)
                successful_repos.append({
                    'name': repo_name,
                    'count': len(swift_file_list),
                    'branch': used_branch,
                    'analyzed_count': min(3, len(swift_file_list))
                })

                total_analyzed_files += min(3, len(swift_file_list))

                print(f"  파일 분석 시작...")
                downloaded = 0
                analyzed = 0

                for i, file_path in enumerate(swift_file_list):
                    token = next(token_cycle)

                    if download_and_analyze_swift_file(repo_name, file_path, token, used_branch):
                        downloaded += 1
                        analyzed += 1

                    progress = (i + 1) / len(swift_file_list) * 100
                    print(f"    진행률: {progress:.1f}% ({i + 1}/{len(swift_file_list)})")

                    # 테스트용: 처음 3개 파일만
                    if i + 1 == 3:
                        print(f"    테스트 모드: 처음 3개 파일만 처리")
                        break

                print(f"  처리 완료: 다운로드 {downloaded}개, 분석 {analyzed}개")

            else:
                failed_repos.append(repo_name)
                print(f"  Swift 파일 없음")

        except Exception as e:
            print(f"  리포지토리 처리 실패: {e}")
            failed_repos.append(repo_name)

        print("-" * 60)

    # 분석 요약 파일 생성
    if successful_repos:
        create_analysis_summary(successful_repos)

    # 최종 결과 요약
    print("\n" + "=" * 60)
    print("🎉 처리 완료!")
    print(f"📊 총 Swift 파일 수: {total_swift_files:,}")
    print(f"🤖 Claude 분석 완료: {total_analyzed_files:,}개")
    print(f"✅ 성공 리포지토리: {len(successful_repos)}")
    print(f"❌ 실패 리포지토리: {len(failed_repos)}")
    print(f"☁️ 분석 결과는 Google Drive에 자동 저장됩니다.")
    print(f"💾 분석 결과는 './analysis_results/' 폴더에 로컬 저장됩니다.")

    if successful_repos:
        print(f"\n📋 성공한 리포지토리 상세:")
        for repo in successful_repos:
            print(f"  • {repo['name']}: {repo['count']}개 발견, {repo['analyzed_count']}개 분석 (브랜치: {repo['branch']})")

    if failed_repos:
        print(f"\n🚨 실패한 리포지토리:")
        for repo in failed_repos:
            print(f"  • {repo}")


if __name__ == "__main__":
    main()