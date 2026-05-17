#!/usr/bin/env python3

import json
import os
import re
import shutil
import sys
from datetime import datetime


def print_usage():
    print(
        "사용법: python3 settingInfoToSourcemeAndYaml.py <입력1: setting.info> <입력2: sourceme> <입력3: sourceme.yaml>"
    )
    sys.exit(1)


# [보강 10] YAML에서 다른 타입으로 파싱될 수 있는 특수값 목록
YAML_SPECIAL = {"true", "false", "null", "yes", "no", "on", "off", "~"}


def escape_tcsh(val):
    # [보강 2] 빈 값(KEY=) 처리
    if not val:
        return '""'
    if re.match(r"^[\w\-\./]+$", val):
        return val
    val = (
        val.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("$", "\\$")
        .replace("`", "\\`")
    )
    return f'"{val}"'


def unescape_tcsh(val):
    val = val.strip()
    # [보강 버그2] 따옴표 하나짜리 오파싱 방지: len >= 2 조건 추가
    if len(val) >= 2 and val.startswith('"') and val.endswith('"'):
        val = val[1:-1]
        # [보강 1] 이스케이프 역순: \\ 먼저 복원
        val = (
            val.replace("\\\\", "\\")
            .replace('\\"', '"')
            .replace("\\$", "$")
            .replace("\\`", "`")
        )
    elif len(val) >= 2 and val.startswith("'") and val.endswith("'"):
        val = val[1:-1]
    return val


def main():
    # 콘솔 인코딩으로 인한 UnicodeEncodeError 방지
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

    # [보강 5] 인자 파싱을 main() 안으로 이동
    if len(sys.argv) != 4:
        print_usage()

    setting_info_file = sys.argv[1]
    sourceme_file = sys.argv[2]
    yaml_file = sys.argv[3]

    # [보강 3] setting.info 파일 존재 여부 명시적 체크
    if not os.path.exists(setting_info_file):
        print(
            f"❌ 오류: 입력 파일 '{setting_info_file}'을 찾을 수 없습니다.",
            file=sys.stderr,
        )
        sys.exit(1)

    lines = []
    active_vars_idx = {}  # {변수명: lines 리스트 내의 인덱스}
    active_raw_values = {}  # {변수명: 원본(Raw) 값}

    # 1. 기존 sourceme 파일 읽기 (누적 및 중복 검사용)
    if os.path.exists(sourceme_file):
        with open(sourceme_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for i, line in enumerate(lines):
            # [보강 버그1] 값 부분을 optional로: setenv KEY 단독 라인도 파싱 가능
            m = re.match(r"^\s*setenv\s+([A-Za-z_][A-Za-z0-9_]*)(?:\s+(.*))?$", line)
            if m:
                key = m.group(1)
                val_tcsh = m.group(2) or ""
                active_vars_idx[key] = i
                active_raw_values[key] = unescape_tcsh(val_tcsh)

    # 2. setting.info 파일 읽기 및 로직 적용
    with open(setting_info_file, "r", encoding="utf-8") as f:
        # ↓ 이 블록 주석을 먼저 추가
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        basename = os.path.basename(setting_info_file)
        lines.append(f"# {'=' * 60}\n")
        lines.append(f"# [{timestamp}] from: {basename}\n")
        lines.append(f"# {'=' * 60}\n")
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip()

                # [보강 6] key 유효성 검증
                if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key):
                    print(
                        f"⚠️  경고 (line {line_no}): 잘못된 변수명 건너뜀 -> '{key}'",
                        file=sys.stderr,
                    )
                    continue

                # [보강 7] 이중 주석(# # setenv) 방지
                if key in active_vars_idx:
                    old_idx = active_vars_idx[key]
                    if not lines[old_idx].lstrip().startswith("#"):
                        lines[old_idx] = "# " + lines[old_idx]

                tcsh_val = escape_tcsh(val)
                new_line = f"setenv {key} {tcsh_val}\n"
                lines.append(new_line)

                active_vars_idx[key] = len(lines) - 1
                active_raw_values[key] = val

            else:
                # [보강 4] '=' 없는 라인 경고
                print(
                    f"⚠️  경고 (line {line_no}): '=' 없는 라인 건너뜀 -> '{line}'",
                    file=sys.stderr,
                )

    # 3. 누적된 sourceme 파일 원자적 저장
    tmp_sourceme = sourceme_file + ".tmp"
    try:
        with open(tmp_sourceme, "w", encoding="utf-8") as f:
            f.writelines(lines)
        shutil.move(tmp_sourceme, sourceme_file)
    except Exception as e:
        print(f"❌ sourceme 파일 저장 실패: {e}", file=sys.stderr)
        if os.path.exists(tmp_sourceme):
            os.remove(tmp_sourceme)
        sys.exit(1)

    # 4. YAML 파일 생성 (최종 활성 변수만, sourceme 라인 순서 기준)
    # [보강 9] 알파벳 정렬 대신 sourceme 활성 라인 순서 기준으로 정렬
    ordered_keys = sorted(active_raw_values.keys(), key=lambda k: active_vars_idx[k])

    tmp_yaml = yaml_file + ".tmp"
    try:
        with open(tmp_yaml, "w", encoding="utf-8") as f:
            for key in ordered_keys:
                val = active_raw_values[key]
                # [보강 10] YAML 특수값은 강제로 따옴표(json.dumps) 처리
                if re.match(r"^[\w\-\./]+$", val) and val.lower() not in YAML_SPECIAL:
                    f.write(f"{key}: {val}\n")
                else:
                    f.write(f"{key}: {json.dumps(val, ensure_ascii=False)}\n")
        shutil.move(tmp_yaml, yaml_file)
    except Exception as e:
        print(f"❌ yaml 파일 저장 실패: {e}", file=sys.stderr)
        if os.path.exists(tmp_yaml):
            os.remove(tmp_yaml)
        sys.exit(1)

    print(f"✅ 처리 완료: '{setting_info_file}' 데이터가 성공적으로 반영되었습니다.")
    print(f"   sourceme : {sourceme_file}")
    print(f"   yaml     : {yaml_file}")


if __name__ == "__main__":
    main()
