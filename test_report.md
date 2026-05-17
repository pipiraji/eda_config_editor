# 📊 EDA Config Editors 통합 테스트 결과 보고서 (Test Report)

본 보고서는 최신 보완 및 구현된 4대 EDA 환경설정 에디터(`qrc`, `starrc`, `setenv`, `icv`)의 다각적인 동작 테스트 결과를 상세히 기록합니다.

--- 

## 1. QRC Config Editor (`qrc_editor.py`) 테스트
QRC 에디터의 옵션 유효성 검사(하이픈 제한) 및 다중 AND 조건 매칭을 확인합니다.

### 1.1 옵션 하이픈('-') 방지 가드 테스트
- **실행 명령어:** `python qrc_editor.py qrc.cmd set --command input_db --option -run_name --value Design`
- **Exit Code:** `2`
- **출력 내용 (에러 메시지):**
```
usage: qrc_editor.py [-h] [--command COMMAND] [--option OPTION]
                     [--value VALUE] [--dry-run] [--output OUTPUT]
                     file {uncomment,update,set,delete}
qrc_editor.py: error: argument --option: expected one argument
```

### 1.2 공백 포함 값 추가 및 저장 테스트
- **실행 명령어:** `python qrc_editor.py qrc.cmd set --command input_db --option run_name --value Design Workspace`
- **결과 파일 내용:**
```tcl
	-type calibre \
	-directory_name ./calibre \
	-run_name Design Workspace \
	-layer_map_file ./layer.map \
	-device_property_value 7 \
	-instance_property_value 6 \
	-net_property_value 5

output_db \
	-type spef \
	-subtype standard

extract \
	-selection all \
	-type rc_decoupled
```

## 2. StarRC Config Editor (`starrc_editor.py`) 테스트
StarRC의 AND 교집합 필터링 기반 주석 제어를 검증합니다.

### 2.1 AND 조건 매칭 주석 해제 테스트 (Value가 YES인 항목)
- **실행 명령어:** `python starrc_editor.py starrc.cmd uncomment --value YES`
- **결과 파일 내용:**
```cmd
*TCAD_GRD_FILE: /path/to/process.nxtgrd
NETLIST_FILE: no
NETLIST_FORMAT: SPF
TOP_CELL_NAME: my_top_cell
EXTRACT_RES: YES
EXTRACT_CAP: YES
NETLIST_FILE2: no
TTT: YES
3TTT: YES
ETTT: YES
```

## 3. tcsh setenv Config Editor (`setenv_editor.py`) 테스트
setenv의 2항 구조 완벽 지원, 공백 포함 시 자동 큰따옴표 랩핑 가드, 그리고 우측 주석 공백 간격 보존을 테스트합니다.

### 3.1 공백 포함 3항 변수 자동 큰따옴표 랩핑 가드 테스트
- **실행 명령어:** `python setenv_editor.py setenv.csh set --variable NEW --value VDD* VSS?`
- **결과 파일 내용:**
```csh
setenv AAAA BBBB
setenv TEST_VAR TEST_VAL
setenv NEW "VDD* VSS?"

setenv VAR_ONLY1
setenv VAR_ONLY2
setenv VAR_ONLY3
```

### 3.2 값 없는 2항 구조 환경 변수 추가 테스트
- **실행 명령어:** `python setenv_editor.py setenv.csh set --variable VAR_ONLY4`
- **결과 파일 내용:**
```csh
setenv VAR_ONLY2
setenv VAR_ONLY3
setenv VAR_ONLY4
```

### 3.3 우측 설명 주석 및 정렬 공백 간격 보존 테스트
- **실행 명령어:** `python setenv_editor.py setenv.csh update --variable PATH --value /new/bin:$PATH`
- **결과 파일 내용:**
```csh

setenv PATH /new/bin:$PATH        # 패스 지정
```

## 4. IC Validator Config Editor (`icv_editor.py`) 테스트
IC Validator의 전역 `#define` 지출 필터링, 조건부 컴파일 구역 및 블록 주석 건너뛰기, Spacing 유지 능력을 검증합니다.

### 4.1 전역(Top-level) 라인 주석 해제 및 블록/조건부 영역 보호 테스트
- **실행 명령어:** `python icv_editor.py icv.pxl uncomment --variable .*_CHECK`
- **결과 파일 내용:**
```c

// [비활성화] 아래 변수들은 주석 처리되어 이번 검사에서 실행되지 않습니다.
#define RUN_LVS_CHECK
#define RUN_ANTENNA_CHECK
// #define ESD_RULE_OPTION_2


// -------------------------------------------------------------------------
// 2. 공정 테크놀로지 옵션 (Technology Options)
//    - 특정 공정 세대나 트랜지스터 구조를 선택하는 다중 변수입니다.
// -------------------------------------------------------------------------

#define PROCESS_NODE_3NM       // 3나노 공정 룰셋 적용
#define ENABLE_FINFET_RULES    // FinFET 구조에 특화된 검사 규칙 활성화

```

### 4.2 값 업데이트 시 Spacing 및 우측 설명 주석 보존 테스트
- **실행 명령어:** `python icv_editor.py icv.pxl update --variable GRID_RESOLUTION --value 0.005`
- **결과 파일 내용:**
```c

// 데이터 해상도 설정
#define GRID_RESOLUTION    0.005 // 제조 그리드 크기 (마이크로미터 단위)

// Metal 1 (M1) 레이어 치수 변수 정의
#define M1_MIN_WIDTH       0.028 // M1 최소 폭 (Width)
#define M1_MIN_SPACING     0.032 // M1 최소 간격 (Spacing)
#define M1_MAX_WIDTH       2.500 // M1 최대 광폭 제한

// Metal 2 (M2) 레이어 치수 변수 정의
#define M2_MIN_WIDTH       0.034 // M2 최소 폭
#define M2_MIN_SPACING     0.038 // M2 최소 간격

// Via 1 (V1) 레이어 치수 및 Enclosure 변수 정의
#define VIA1_SIZE          0.030 // Via1 가로/세로 정방형 크기
```
