# 🛠️ EDA Config Editor Suite

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

**EDA Config Editor Suite**는 반도체 설계 및 검증 과정에서 널리 활용되는 주요 **EDA (Electronic Design Automation) 툴들의 핵심 구성 파일들을 CLI 터미널 환경에서 고도로 안전하고 정밀하게 편집/자동화하는 종합 스크립트 도구 묶음**입니다.

주석 처리 해제(`uncomment`), 값 업데이트(`update`), 신규 설정 추가(`set`), 주석 비활성화(`delete`)의 4대 핵심 파이프라인 흐름을 완벽히 구축하고 있으며, EDA 파일 특유의 복잡하고 엄격한 문법과 코딩 스타일(Spacing, 정렬 주석)을 보존하는 강력한 **세이프티 가드(Safety Guards)**를 자랑합니다.

---

## 🚀 주요 특징 (Key Features)

* **정밀 Spacing & 정렬 주석 보존 (Spacing Preservation)**
  * EDA 엔지니어가 가독성을 위해 설정해 둔 값과 설명 주석 사이의 공백 간격을 훼손 없이 캐릭터 단위로 감지하여 보존합니다.
* **2항 & 3항 구조 완벽 혼용**
  * 값 없는 2항 선언(예: `setenv VAR`, `#define FLAG`)과 값이 매핑된 3항 선언(예: `setenv VAR VAL`, `#define CONST 0.05`)을 자동으로 인식하고 생성합니다.
* **고급 구역 보호 가드 (Block & Condition Guard)**
  * 블록 주석(`/* ... */`) 내부에 작성된 지시문이나 조건부 컴파일 분기 구문(`#ifdef`, `#ifndef`) 내부의 매크로들을 매칭에서 완벽하게 제외하여 컴파일 및 런셋 부작용을 사전에 차단합니다.
* **강력한 정규표현식(Regex) 필터링 & AND 매칭**
  * 여러 필터 조건(--variable, --value, --option 등)을 입력 시, 교집합(AND)으로 만족하는 타겟만을 엄격하게 식별하여 제어합니다.
* **쉘 문법 안전 규격화**
  * `tcsh` 환경 변수 등 값에 공백이 있을 때 발생하기 쉬운 구문 에러를 예방하기 위해 자동 큰따옴표 랩핑 및 특수문자 이스케이프 가드가 내장되어 있습니다.

---

## 📂 프로젝트 구성 및 파일 소개

본 프로젝트는 각 EDA 툴별로 독립된 서브디렉토리에 에디터 스크립트, 설정 파일, 그리고 상세 개별 계획서를 동봉하여 모듈식 구조로 설계되었습니다.

```text
config_editor/
├── README.md                 # 통합 가이드 문서 (본 파일)
├── run_tests.py              # 통합 테스트 실행 스크립트
├── test_report.md            # [자동 생성] 통합 테스트 결과 보고서
├── qrc/                      # Cadence QRC 툴 폴더
│   ├── qrc_editor.py
│   ├── qrc.cmd
│   └── qrc.md
├── starrc/                   # Synopsys StarRC 툴 폴더
│   ├── starrc_editor.py
│   ├── starrc.cmd
│   └── starrc.md
├── setenv/                   # tcsh 환경변수 툴 폴더
│   ├── setenv_editor.py
│   ├── setenv.csh
│   └── setenv.md
├── icv/                      # Synopsys IC Validator 툴 폴더
│   ├── icv_editor.py
│   ├── icv.pxl
│   └── icv.md
└── _convert_info_to_env/     # 환경변수 일괄 변환 도구 폴더
    ├── info_to_env_converter.py
    ├── info_to_env_converter.md
    ├── setting.info
    ├── sourceme.csh
    └── sourceme.yaml
```

| 에디터 스크립트 | 대상 EDA 툴 / 구성 파일 | 핵심 특징 |
| :--- | :--- | :--- |
| **`qrc/qrc_editor.py`** | Cadence QRC (`qrc/qrc.cmd`) | 옵션명 하이픈(`-`) 방지 및 다중 계층(Command -> Option -> Value) AND 제어 |
| **`starrc/starrc_editor.py`** | Synopsys StarRC (`starrc/starrc.cmd`) | 심플한 Key-Value 구조의 주석 제어 및 강력한 AND 조건 필터링 |
| **`setenv/setenv_editor.py`** | `tcsh` 환경 변수 (`setenv/setenv.csh`) | 2항/3항 완벽 지원, 공백 포함 값 자동 큰따옴표 랩핑 및 주석 Spacing 보존 |
| **`icv/icv_editor.py`** | Synopsys IC Validator (`icv/icv.pxl`) | 블록 주석 및 `#ifdef` 보호 가드, 우측 설명 주석 Spacing 정밀 보존 |
| **`_convert_info_to_env/info_to_env_converter.py`** | 설정 변환기 (`_convert_info_to_env/setting.info`) | `.info` 설정을 `sourceme.csh` 및 `sourceme.yaml`로 중복 가드 및 원자적 변환 |

---

## 💻 사용 방법 (Usage Examples)

### 1. Cadence QRC
```bash
# 특정 command 하위의 특정 option의 값을 업데이트
python qrc/qrc_editor.py qrc/qrc.cmd set --command input_db --option run_name --value "Design Workspace"
```

### 2. Synopsys StarRC
```bash
# 값이 YES인 설정들만 골라내어 일괄 주석 해제(uncomment)
python starrc/starrc_editor.py starrc/starrc.cmd uncomment --value YES
```

### 3. tcsh 환경 변수 (setenv)
```bash
# 공백이 포함된 변수를 추가 (자동으로 큰따옴표가 붙어 3항 문법 수호)
python setenv/setenv_editor.py setenv/setenv.csh set --variable NEW --value "VDD* VSS?"

# 2항 구조의 빈 환경변수 추가
python setenv/setenv_editor.py setenv/setenv.csh set --variable VAR_ONLY4
```

### 4. Synopsys IC Validator (#define)
```bash
# 조건부 컴파일 구역을 안전하게 우회하며 전역 CHECK 변수들만 주석 해제
python icv/icv_editor.py icv/icv.pxl uncomment --variable ".*_CHECK"

# 기존 Spacing 정렬 간격을 그대로 지키며 값 업데이트
python icv/icv_editor.py icv/icv.pxl update --variable GRID_RESOLUTION --value 0.005
```

### 5. 설정 정보 변환기 (Info-to-Env Converter)
```bash
# setting.info에 등록된 신규 정보들을 sourceme.csh(쉘 환경변수) 및 sourceme.yaml에 자동 병합
python _convert_info_to_env/info_to_env_converter.py _convert_info_to_env/setting.info _convert_info_to_env/sourceme.csh _convert_info_to_env/sourceme.yaml
```

---

## 🧪 통합 자동 테스트 기동 (Run Tests)

워크스페이스 내에 내장된 통합 테스트 시나리오 스크립트(`run_tests.py`)를 통해 전체 에디터의 주요 엣지 케이스 동작을 클릭 한 번으로 검증할 수 있습니다.

```bash
# 통합 테스트 기동
python run_tests.py
```
* 실행 시 원본 설정 파일들을 자동으로 백업한 후 복구하며, 전체 에디터의 실제 실행 로그 및 결과 단락을 기록하는 **[test_report.md](./test_report.md)** 보고서를 자동 생성합니다.

---

## 📝 License
This project is licensed under the MIT License - see the LICENSE file for details.
