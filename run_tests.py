import subprocess
import os
import shutil

# Files to backup and test
TEST_FILES = {
    "qrc/qrc.cmd": "qrc/qrc.cmd.bak",
    "starrc/starrc.cmd": "starrc/starrc.cmd.bak",
    "setenv/setenv.csh": "setenv/setenv.csh.bak",
    "icv/icv.pxl": "icv/icv.pxl.bak"
}

def backup_files():
    print("Backing up configuration files...")
    for original, backup in TEST_FILES.items():
        if os.path.exists(original):
            shutil.copy(original, backup)
            print(f"  Backed up {original} to {backup}")

def restore_files():
    print("Restoring original configuration files...")
    for original, backup in TEST_FILES.items():
        if os.path.exists(backup):
            shutil.move(backup, original)
            print(f"  Restored {original} from {backup}")

def run_cmd(args):
    cmd_str = "python " + " ".join(args)
    print(f"\nExecuting: {cmd_str}")
    result = subprocess.run(["python"] + args, capture_output=True, text=True)
    return {
        "command": cmd_str,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "code": result.returncode
    }

def read_file_segment(filepath, keyword=None, lines_count=15):
    if not os.path.exists(filepath):
        return "File not found"
    
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    if keyword:
        # Return lines surrounding the keyword
        for i, line in enumerate(lines):
            if keyword in line:
                start = max(0, i - 2)
                end = min(len(lines), i + lines_count - 2)
                return "".join(lines[start:end])
    
    # Otherwise return the last lines_count lines
    return "".join(lines[-lines_count:])

def main():
    backup_files()
    
    report_content = []
    report_content.append("# 📊 EDA Config Editors 통합 테스트 결과 보고서 (Test Report)\n")
    report_content.append("본 보고서는 최신 보완 및 구현된 4대 EDA 환경설정 에디터(`qrc`, `starrc`, `setenv`, `icv`)의 다각적인 동작 테스트 결과를 상세히 기록합니다.\n")
    report_content.append("--- \n")

    try:
        # =========================================================================
        # 1. QRC Editor Tests
        # =========================================================================
        report_content.append("## 1. QRC Config Editor (`qrc/qrc_editor.py`) 테스트")
        report_content.append("QRC 에디터의 옵션 유효성 검사(하이픈 제한) 및 다중 AND 조건 매칭을 확인합니다.\n")
        
        # Test 1.1: Hyphen safeguard on option name
        res = run_cmd(["qrc/qrc_editor.py", "qrc/qrc.cmd", "set", "--command", "input_db", "--option", "-run_name", "--value", "Design"])
        report_content.append("### 1.1 옵션 하이픈('-') 방지 가드 테스트")
        report_content.append(f"- **실행 명령어:** `{res['command']}`")
        report_content.append(f"- **Exit Code:** `{res['code']}`")
        report_content.append(f"- **출력 내용 (에러 메시지):**\n```\n{res['stderr'] or res['stdout']}\n```\n")

        # Test 1.2: Normal Set & Spaces Quoting Value
        res = run_cmd(["qrc/qrc_editor.py", "qrc/qrc.cmd", "set", "--command", "input_db", "--option", "run_name", "--value", "Design Workspace"])
        segment = read_file_segment("qrc/qrc.cmd", keyword="run_name")
        report_content.append("### 1.2 공백 포함 값 추가 및 저장 테스트")
        report_content.append(f"- **실행 명령어:** `{res['command']}`")
        report_content.append(f"- **결과 파일 내용:**\n```tcl\n{segment}```\n")

        # =========================================================================
        # 2. StarRC Editor Tests
        # =========================================================================
        report_content.append("## 2. StarRC Config Editor (`starrc/starrc_editor.py`) 테스트")
        report_content.append("StarRC의 AND 교집합 필터링 기반 주석 제어를 검증합니다.\n")

        # Test 2.1: Uncommenting matching and logic
        res = run_cmd(["starrc/starrc_editor.py", "starrc/starrc.cmd", "uncomment", "--value", "YES"])
        segment = read_file_segment("starrc/starrc.cmd")
        report_content.append("### 2.1 AND 조건 매칭 주석 해제 테스트 (Value가 YES인 항목)")
        report_content.append(f"- **실행 명령어:** `{res['command']}`")
        report_content.append(f"- **결과 파일 내용:**\n```cmd\n{segment}```\n")

        # =========================================================================
        # 3. Setenv Editor Tests
        # =========================================================================
        report_content.append("## 3. tcsh setenv Config Editor (`setenv/setenv_editor.py`) 테스트")
        report_content.append("setenv의 2항 구조 완벽 지원, 공백 포함 시 자동 큰따옴표 랩핑 가드, 그리고 우측 주석 공백 간격 보존을 테스트합니다.\n")

        # Test 3.1: 3-term Auto Quoting Guard
        res = run_cmd(["setenv/setenv_editor.py", "setenv/setenv.csh", "set", "--variable", "NEW", "--value", "VDD* VSS?"])
        segment = read_file_segment("setenv/setenv.csh", keyword="NEW")
        report_content.append("### 3.1 공백 포함 3항 변수 자동 큰따옴표 랩핑 가드 테스트")
        report_content.append(f"- **실행 명령어:** `{res['command']}`")
        report_content.append(f"- **결과 파일 내용:**\n```csh\n{segment}```\n")

        # Test 3.2: 2-term support
        res = run_cmd(["setenv/setenv_editor.py", "setenv/setenv.csh", "set", "--variable", "VAR_ONLY4"])
        segment = read_file_segment("setenv/setenv.csh", keyword="VAR_ONLY4")
        report_content.append("### 3.2 값 없는 2항 구조 환경 변수 추가 테스트")
        report_content.append(f"- **실행 명령어:** `{res['command']}`")
        report_content.append(f"- **결과 파일 내용:**\n```csh\n{segment}```\n")

        # Test 3.3: Trailing comment spacing preservation
        # First we put PATH back to original but with comment
        with open("setenv/setenv.csh", 'w', encoding='utf-8') as f:
            f.write('\nsetenv PATH "/usr/local/bin:$PATH"        # 패스 지정\n')
        
        res = run_cmd(["setenv/setenv_editor.py", "setenv/setenv.csh", "update", "--variable", "PATH", "--value", "/new/bin:$PATH"])
        segment = read_file_segment("setenv/setenv.csh", keyword="PATH")
        report_content.append("### 3.3 우측 설명 주석 및 정렬 공백 간격 보존 테스트")
        report_content.append(f"- **실행 명령어:** `{res['command']}`")
        report_content.append(f"- **결과 파일 내용:**\n```csh\n{segment}```\n")

        # =========================================================================
        # 4. IC Validator Editor Tests
        # =========================================================================
        report_content.append("## 4. IC Validator Config Editor (`icv/icv_editor.py`) 테스트")
        report_content.append("IC Validator의 전역 `#define` 지출 필터링, 조건부 컴파일 구역 및 블록 주석 건너뛰기, Spacing 유지 능력을 검증합니다.\n")

        # Test 4.1: Top-level line comment uncommenting
        res = run_cmd(["icv/icv_editor.py", "icv/icv.pxl", "uncomment", "--variable", ".*_CHECK"])
        segment = read_file_segment("icv/icv.pxl", keyword="RUN_LVS_CHECK")
        report_content.append("### 4.1 전역(Top-level) 라인 주석 해제 및 블록/조건부 영역 보호 테스트")
        report_content.append(f"- **실행 명령어:** `{res['command']}`")
        report_content.append(f"- **결과 파일 내용:**\n```c\n{segment}```\n")

        # Test 4.2: Space & Comments Alignment Preservation
        res = run_cmd(["icv/icv_editor.py", "icv/icv.pxl", "update", "--variable", "GRID_RESOLUTION", "--value", "0.005"])
        segment = read_file_segment("icv/icv.pxl", keyword="GRID_RESOLUTION")
        report_content.append("### 4.2 값 업데이트 시 Spacing 및 우측 설명 주석 보존 테스트")
        report_content.append(f"- **실행 명령어:** `{res['command']}`")
        report_content.append(f"- **결과 파일 내용:**\n```c\n{segment}```\n")

        # Write final markdown report
        with open("test_report.md", "w", encoding="utf-8") as f:
            f.write("\n".join(report_content))
            
        print("\n" + "="*50)
        print("All scenarios executed successfully! Report saved to 'test_report.md'.")
        print("="*50)

    finally:
        restore_files()

if __name__ == "__main__":
    main()
