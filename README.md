# BookOasis 독서 업적

BookOasis에 저장된 독서 진행 기록을 이용해 사용자별 업적, 배지, 연속 독서와 다음 목표를 보여주는 독립 카테고리 플러그인입니다.

![독서 업적 전용 탭](docs/achievements-tab.png?v=1.1.0)

## 버전 및 호환 정보

| 항목 | 값 |
| --- | --- |
| 플러그인 버전 | `1.1.0` |
| 플러그인 ID | `achievements` |
| 클래스 | `AchievementsMetadataProvider` |
| 모듈 | `plugins.metadata.achievements.achievements` |
| 유형 | 사용자별 독서 업적 카테고리 UI 제공자 |
| 확인한 BookOasis 버전 | `1.8.7` |
| 문서 작성일 | `2026-08-09` |

이 플러그인은 BookOasis의 권장 폴더형 플러그인 구조와 `PluginDatabaseGateway`를 사용합니다. BookOasis 공통 UI나 코어 파일을 수정하지 않으며 Activity 및 Activity Desk 플러그인에 의존하지 않습니다.

## 주요 기능

- 현재 로그인 사용자의 독서 활동만 집계합니다.
- 첫 독서와 첫 완독 업적을 제공합니다.
- 누적 완독 5권, 10권, 25권, 50권과 100권 업적을 제공합니다.
- 고정 페이지 도서의 현재 진행 페이지 합계를 기준으로 1,000페이지, 5,000페이지와 10,000페이지 업적을 제공합니다.
- 3일, 7일, 14일과 30일 연속 독서 업적을 제공합니다.
- 완독 도서의 장르와 태그를 기준으로 탐험 업적을 제공합니다.
- 오디오북 첫 청취, 첫 완청과 누적 완청 업적을 제공합니다.
- 전체 업적 진행률, 상태별 개수와 다음 업적까지 남은 수치를 표시합니다.
- 달성, 진행 중과 잠김 상태 필터를 제공합니다.
- 일반·성인 도서의 Redis pending 진행률을 DB 결과에 병합합니다.
- 이미 달성한 업적은 영구 보존하고 `(user_id, achievement_key)` 기본 키로 중복 지급을 막습니다.
- 사용자 권한에 따라 접근 가능한 일반·성인·오디오북 서재만 집계합니다.
- 데스크톱 5열부터 모바일 1열까지 반응형 카드 화면을 제공합니다.

## 화면 구성

`achievements`는 `category_tab` 계약을 사용하는 좌측 사이드바의 `독서 업적` 카테고리입니다. 상단에는 전체 달성률, 완독 권수, 고정 페이지, 현재 연속 독서, 오디오북 완청과 다음 업적을 표시합니다.

본문은 첫걸음, 완독, 독서량, 연속 독서, 탐험과 오디오북 카테고리로 구분합니다. 각 카드는 희귀도, 목표, 현재 진행률과 달성일을 표시합니다.

## 설정

현재 버전은 별도 사용자 설정을 제공하지 않습니다. 업적 정의와 임계값은 `definitions.py`에서 버전 관리하며, 해금 상태는 사용자별로 저장합니다.

| 업적 분류 | 기준 |
| --- | --- |
| 첫걸음 | 첫 도서 진행 기록 |
| 완독 | 완료한 일반·성인 도서 권수 |
| 독서량 | 고정 페이지 형식의 현재 진행 페이지 합계 |
| 연속 독서 | 양수 페이지 변화가 기록된 연속 날짜 |
| 탐험 | 완독 도서의 서로 다른 장르·태그 수 |
| 오디오북 | 청취를 시작하거나 완청한 오디오북 권수 |

## 설치

최종 폴더 구조는 다음과 같습니다.

```text
plugins/metadata/
└── achievements/
    ├── __init__.py
    ├── achievements.py
    ├── definitions.py
    ├── index.html
    ├── style.css
    ├── script.js
    └── VERSION
```

BookOasis의 `plugins/metadata/`에서 다음 명령을 실행합니다.

```bash
git clone https://github.com/colaiuta77/achievements.git achievements
```

1. BookOasis 서버를 재시작합니다.
2. `환경설정 > 플러그인 설정`에서 `독서 업적`을 활성화합니다.
3. 좌측 사이드바의 `독서 업적` 카테고리를 확인합니다.

업데이트할 때는 BookOasis의 `plugins/metadata/`에서 다음 명령을 실행합니다.

```bash
git -C achievements pull --ff-only
```

### 자동 업데이트

버전 1.1.0부터 BookOasis의 `update_manifest` 계약과 `VERSION` 파일을 지원합니다. GitHub 버전이 현재 버전보다 높을 때 `achievements.py`, `definitions.py`, `__init__.py`, `VERSION`, `index.html`, `style.css`와 `script.js`를 함께 갱신합니다.

1.1.0 미만 설치본에는 GitHub 업데이트 선언이 없으므로 위 `git pull` 방식이나 폴더 교체 방식으로 1.1.0 이상을 한 번 설치해야 합니다. 이후에는 BookOasis의 플러그인 업데이트 기능을 사용할 수 있습니다.

Docker 환경에서는 BookOasis 소스가 연결된 호스트 볼륨 또는 컨테이너의 동일한 경로에 설치해야 합니다. BookOasis 업데이트 후에도 플러그인 폴더가 유지되는지 확인하세요.

## 데이터와 보안

- 로그인 사용자 권위와 성인·오디오북 접근 권한은 general DB의 `users`를 기준으로 합니다.
- 일반·성인 도서는 `books`, `user_progress`, `user_reading_log`를 DB Gateway로 조회합니다.
- 오디오북은 `audiobooks`, `audiobook_progress`의 청취 시간·진행률·완청 상태를 조회합니다.
- 일반·성인 도서의 `sync:progress:pending`과 `user:progress` Redis 키를 읽어 아직 flush되지 않은 진행률을 병합합니다.
- Redis를 사용할 수 없거나 데이터가 손상된 경우 해당 항목을 건너뛰고 DB 결과를 사용합니다.
- 삭제된 도서와 사용자에게 접근 권한이 없는 서재는 집계에서 제외합니다.
- 사용자별 해금 상태는 활성 general DB의 `plugin_achievement_unlocks` 테이블에 저장합니다.
- SQLite 구성에서는 general SQLite DB에, MariaDB 구성에서는 general MariaDB에 저장합니다.
- 플러그인 디렉터리에 별도 업적 SQLite 파일을 만들지 않습니다.
- UI 데이터 요청마다 Flask 세션의 현재 사용자를 다시 확인합니다.
- 동적 사용자 데이터는 임의 HTML로 삽입하지 않고 안전한 DOM `textContent`로 렌더링합니다.
- 메타데이터 검색과 적용은 지원하지 않습니다.

## 제한 사항

- 페이지 업적은 `7z`, `cbz`, `cbr`, `pdf`, `rar`, `tar`와 `zip` 형식만 집계합니다. EPUB과 TXT의 진행률은 페이지 수와 혼합하지 않습니다.
- 페이지 업적은 도서별 현재 최고 진행 페이지 합계이며 과거 재독 페이지를 누적 합산하지 않습니다.
- 과거에 DB에 flush되지 않고 Redis에서도 사라진 진행 기록은 복구할 수 없습니다.
- 오디오북의 누적 실제 청취 시간 이력이 없어 현재 버전은 시작·완청 권수만 제공합니다.
- 심야·주말 독서 업적은 신뢰할 수 있는 과거 세션 시간 계약이 없어 포함하지 않습니다.
- 장르와 태그는 BookOasis가 저장한 쉼표 구분 값을 기준으로 계산합니다.
- 이미 해금한 업적은 이후 원본 진행률이 줄어도 유지됩니다.
- 현재 버전에는 사용자용 업적 초기화 UI가 없습니다.
- BookOasis의 플러그인 계약 또는 DB 스키마가 변경되면 호환성 업데이트가 필요할 수 있습니다.

## 검증

```powershell
python -m py_compile __init__.py achievements.py definitions.py
node --check script.js
```

SQLite fixture 테스트와 개발용 QA 문서는 로컬에서 검증했으며 GitHub 배포본에는 포함하지 않습니다. MariaDB는 공용 SQL 정적 호환성을 확인했으며 실제 MariaDB 연결 통합 테스트와는 구분합니다.

## 변경 이력

### 1.1.0 - 2026-08-09

- BookOasis 1.8.7 네이티브 `category_tab` 전용 독서 업적 화면 공개.
- 첫 독서·완독, 누적 완독, 고정 페이지, 연속 독서, 탐험과 오디오북 업적 22개 제공.
- 전체 달성률, 상태 필터, 다음 업적과 반응형 희귀도 카드 UI 추가.
- SQLite·MariaDB 공용 `PluginDatabaseGateway` 기반 사용자별 해금 저장소 추가.
- 일반·성인 Redis pending 진행률 병합과 general 사용자 권위·서재 권한 적용.
- GitHub raw 기반 자동 업데이트 계약 추가.
- 실제 BookOasis 다크 테마 화면으로 README 스크린샷 추가.

### 1.0.1 - 2026-08-09

- 구버전 Python에서 `int.is_integer()`를 지원하지 않아 업적 응답 생성이 실패하던 호환 오류 수정.
- 경계값을 명시적인 `float`로 정규화하고 숫자 표시 회귀 테스트 추가.

### 1.0.0 - 2026-08-09

- 사용자별 독서 업적 정의와 영구 해금 상태 저장 기능 추가.
- 일반·성인 도서, 연속 독서, 장르·태그와 오디오북 지표 집계 추가.
- 달성, 진행 중, 잠김 상태를 구분하는 BookOasis 전용 카테고리 UI 추가.

## 라이선스

이 저장소의 [LICENSE](LICENSE)를 따릅니다.
