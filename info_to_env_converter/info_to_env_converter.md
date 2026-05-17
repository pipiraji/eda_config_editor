# 📄 Info-to-Env 환경설정 변환기 계획서 및 명세서

## 1. 시스템 개요

본 스크립트(`info_to_env_converter.py`)는 일반적인 `KEY=VALUE` 형식의 설정 정보 파일(`.info`)을 파싱하여, EDA 환경 설정에 널리 활용되는 **tcsh 쉘 스크립트(`setenv`)** 및 **구조화된 설정 파일(YAML)** 형식으로 정밀하게 마이그레이션 및 자동 병합(Merge)해 주는 환경설정 허브 변환 도구입니다.

### 1.1 용어 및 파일 구조 정의

* **설정 정보 파일 (setting.info):** 공백이나 특수 문자가 허용되는 평면형 `KEY=VALUE` 형식 파일.
* **tcsh 쉘 스크립트 (sourceme.csh):** C-shell 계열 환경 변수 선언 명령어 모음 (`setenv KEY "VALUE"`).
* **설정 파일 (sourceme.yaml):** 계층 구조나 빌드 툴에서 환경 설정을 통째로 캐싱하기 위해 활용하는 YAML 구조화 파일 (`KEY: VALUE`).

---

## 2. 핵심 설계 원칙 및 기능 (Core Features)

1. **원자적 쓰기 (Atomic File Writing):**
   변환 도중 디스크 가득 참(Disk Full)이나 중단 상황이 생기더라도 기존 원본 파일이 손상되거나 빈 파일로 채워지는 불상사를 방지하기 위해, 모든 파일 저장은 임시 파일(`.tmp`)에 완전하게 기록한 뒤 `shutil.move`를 사용하여 **원자적으로 한 번에 대체(Overwrite)** 시킵니다.

2. **중복 변수 자동 비활성화 (Duplicate Guard):**
   `setting.info`로부터 새로운 변수가 입력될 때, 기존 `sourceme.csh` 내에 이미 활성화되어 있던 동일한 키의 변수 라인이 있다면 이를 그냥 지우거나 덮어쓰는 대신 **맨 앞에 `# `를 자동으로 삽입하여 비활성(주석) 처리**함으로써 히스토리 기록을 고스란히 보존합니다.

3. **YAML 특수문자 및 타입 보호 가드 (YAML Special Value Escaping):**
   YAML 파서에서 스트링이 아닌 불리언이나 Null 객체 등으로 자동 파싱되어 파이프라인 에러를 유발하기 쉬운 특수 키워드들(`true`, `false`, `null`, `yes`, `no`, `on`, `off`, `~` 등)을 엄격하게 사전 감지하여, 해당 키워드가 값으로 올 경우 **자동으로 큰따옴표 따옴표 래핑(JSON 직렬화 포맷) 처리**를 거쳐 순수한 문자열 규격으로 저장되도록 방어합니다.

4. **활성 라인 순서 정렬 유지 (Order Preservation):**
   변환되어 최종 출력되는 `sourceme.yaml` 파일은 기계적인 알파벳 정렬 대신, 엔지니어가 작성한 로직과 선언 시퀀스의 인덱스를 기억하여 **`sourceme.csh`의 활성 라인 등장 순서 그대로 정렬**을 매핑하여 가독성을 극대화합니다.

5. **공백 포함 값 자동 이스케이프 및 따옴표 처리:**
   값 내부에 공백이나 이스케이프가 필요한 특수문자(`\`, `"`, `$`, `` ` `` 등)가 포함된 경우 tcsh 규격에 맞춰 자동 백슬래시 이스케이프 처리를 수행하고 큰따옴표로 감싸 안전한 쉘 환경 변수로 규격화합니다.

---

## 3. 사용 방법 및 CLI 실행 가이드

### 3.1 실행 형식
```bash
python _convert_info_to_env/info_to_env_converter.py [setting.info 파일] [sourceme.csh 파일] [sourceme.yaml 파일]
```

### 3.2 실행 예시
```bash
# setting.info의 환경 데이터를 sourceme.csh 및 sourceme.yaml에 일괄 적용
python _convert_info_to_env/info_to_env_converter.py _convert_info_to_env/setting.info _convert_info_to_env/sourceme.csh _convert_info_to_env/sourceme.yaml
```

---

## 4. 예외 처리 및 터미널 안정성 확보 (Safety Guards)

1. **입력 파일 체크 가드 (Exist check):**
   입력 데이터 소스가 될 `.info` 파일의 부재 상황을 사전에 감지하여 `sys.stderr`로 깨끗한 에러 피드백을 전달하고 즉시 `sys.exit(1)`로 세션 안전 종료를 제어합니다.
2. **잘못된 변수명 및 포맷 감지:**
   변수 이름이 표준 C-식별자 패턴(`^[A-Za-z_][A-Za-z0-9_]*$`)을 위반하거나 대입 기호(`=`)가 빠진 불량 설정 라인이 있을 경우 건너뛰고 터미널 경고 메시지를 로그로 남깁니다.
3. **콘솔 인코딩 에러 방지 (Standard Encoding Guard):**
   영어권/아시아권 등 OS 언어팩 환경에 맞춰 표준 입출력 스트림의 인코딩을 UTF-8 대체 모드로 강제 구성하여, 콘솔 인코딩 제한으로 인한 예기치 못한 스크립트 비정상 중단(UnicodeEncodeError)을 차단합니다.
