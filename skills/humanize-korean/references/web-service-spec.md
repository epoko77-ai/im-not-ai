# Humanize KR 웹 서비스 스펙 (Phase 5에서만 로드)

Humanize Korean 파이프라인을 일반 사용자용 웹앱으로 확장할 때 아키텍트가 따르는 참조. 기본 윤문 파이프라인이 안정화된 뒤에만 읽는다.

## 목차

1. 서비스 콘셉트
2. 기술 스택
3. 아키텍처 토폴로지
4. API 스펙
5. UX 플로우
6. 데이터 모델
7. 요금·쿼터·인증
8. 배포·운영
9. 확장 로드맵

## 1. 서비스 콘셉트

**한 줄 설명**: AI가 쓴 한글을 붙여 넣으면 "사람이 쓴 것처럼" 윤문해주는 서비스.

**핵심 가치**:
- **근거 제시**: 어디가 왜 AI 티인지 카테고리별 하이라이트.
- **내용 불변 보증**: 사실·수치·인용이 바뀌지 않았음을 diff로 시각화.
- **한국어 특화**: 번역투·영어 용어 과다 등 한글 고유 패턴에 특화.

**경쟁 차별점**:
- 기존 영어 중심 humanizer(QuillBot·Hix·Undetectable AI)가 한국어에 약함.
- 단순 재작성이 아닌 "탐지 → 근거 → 수술적 윤문" 3단계.

## 2. 기술 스택

- **프레임워크**: Next.js 15 App Router + React Server Components.
- **런타임**: Vercel Fluid Compute (기본 Node.js 24 LTS).
- **AI**: Vercel AI Gateway — Claude(탐지·윤문) + GPT(교차 검증 옵션).
- **스타일**: Tailwind CSS v4 + shadcn/ui + Pretendard 자동 로딩.
- **상태**: useActionState + SSE 스트리밍.
- **캐시**: Runtime Cache API (입력 해시 기반 결과 재활용).
- **DB (옵션)**: Neon Postgres (히스토리 저장 시만).
- **인증 (옵션)**: Clerk Marketplace.
- **이메일 (옵션)**: Resend (가입 확인·요금제 알림).

## 3. 아키텍처 토폴로지

```
[Browser]
    ↓ POST /api/humanize (stream: true)
[Routing Middleware]
    ├─ BotID 검증
    ├─ 쿼터 확인 (Runtime Cache)
    └─ 언어 감지 (한글 아니면 400)
    ↓
[Next.js App Router · Fluid Compute]
    ↓
[Vercel Workflow — durable orchestration]
    ├─ step: detect()         ← AI Gateway → Claude Haiku
    ├─ step: rewrite()        ← AI Gateway → Claude Opus
    ├─ step: fidelity_audit() ← AI Gateway → Claude Sonnet
    └─ step: review()         ← AI Gateway → GPT-5 (옵션)
    ↓ stream SSE
[Browser EventSource]
```

Workflow는 각 step 실패 시 재시도·부분 응답을 허용한다. detect 단계 완료 즉시 하이라이트가 먼저 스트리밍되어 체감 지연을 줄인다.

## 4. API 스펙

### `POST /api/humanize`
**입력:**
```json
{
  "text": "…",
  "genre": "auto | column | report | blog | formal",
  "min_severity": "S1 | S2 | S3",
  "options": {
    "preserve_formatting": false,
    "cross_validate_with_gpt": false,
    "stream": true
  }
}
```

**응답 (SSE):**
```
event: detection_meta
data: {"detected_count":37,"score":71.5,"estimated_genre":"column"}

event: detection_finding
data: {"id":"f001","category":"A-2","severity":"S1","start":142,"end":153,"text_span":"데이터 분석을 통해","reason":"..."}
...

event: rewrite_chunk
data: {"delta":"데이터를 분석해 인사이트를 얻는다."}
...

event: audit_verdict
data: {"verdict":"full_pass"}

event: review_verdict
data: {"verdict":"accept","quality_level":"A","score_after":18.2}

event: final
data: {"rewrite_text":"…","summary":{...}}
```

**에러 코드:**
- 400: 입력 검증 실패 (비한국어·길이 초과·빈 문자열).
- 401: 인증 필요 (유료 플랜 API).
- 429: 쿼터 초과.
- 502: AI Gateway upstream 실패.
- 504: Workflow 타임아웃.

### 개별 라우트

- `POST /api/detect` — 탐지만 (리포트 JSON 반환).
- `POST /api/rewrite` — 탐지 결과를 같이 주면 윤문만.
- `POST /api/review` — 윤문본을 주면 재평가만.
- `GET /api/runs/:id` — 저장된 히스토리 (인증 사용자).
- `DELETE /api/runs/:id` — 히스토리 삭제.

## 5. UX 플로우

### 화면 1 — 랜딩·입력
- 좌측: 붙여넣기 textarea (최대 10,000자, 현재 글자 수 표시).
- 우측: 사이드 패널
  - 장르 라디오 (자동·칼럼·리포트·블로그·공적).
  - 엄격도 슬라이더 (S1만 / S2+ / 전체).
  - 옵션 토글: "영어 인용 유지", "이모지 유지" (기본 꺼짐).
- 하단: "윤문하기" 1 버튼. 익명 사용자는 남은 횟수 표시.

### 화면 2 — 처리 진행 (스트리밍)
- 탐지 하이라이트가 실시간으로 문서에 그려짐.
- 우측 사이드: 카테고리별 카운트 막대 그래프.
- 윤문 시작되면 하단 영역에 토큰 스트림.

### 화면 3 — 좌우 diff 뷰
- 좌: 원문 + 카테고리 하이라이트.
- 우: 윤문본 + 변경 영역 강조.
- 상단 배지: `변경률 18% · S1 0 잔존 · 점수 71.5 → 18.2 · 등급 A`.
- 우측 패널: 주요 변경 3~5건 (before/after 카드).

### 화면 4 — 완료·액션
- "윤문본 복사" / ".md 다운로드" / "2차 윤문" / "피드백 보내기" 버튼.
- 하단 보증 문구: "내용은 수정되지 않았습니다. 사실·수치·인용은 원문과 동일합니다."

### 화면 5 — 히스토리 (인증 사용자)
- 최근 50건의 run 목록.
- 각 run 카드에 입력 시각·길이·점수 개선·등급.
- 개별 클릭 시 화면 3(diff 뷰) 재현.

## 6. 데이터 모델 (Neon Postgres 옵션)

### 테이블

**users** (Clerk 연동)
- `id` (Clerk user_id 매핑)
- `plan` (anonymous / free / pro)
- `quota_daily` (integer)
- `created_at`

**humanize_runs**
- `id` (uuid)
- `user_id` (nullable, 익명 허용)
- `input_hash` (sha256, 중복 탐지용)
- `input_length`
- `estimated_genre`
- `score_before`, `score_after`
- `change_rate`
- `quality_level` (A/B/C/D)
- `created_at`
- `retain_content` (bool — 사용자가 본문 저장 동의했는지)

**run_contents** (retain_content = true 일 때만)
- `run_id`
- `input_text`, `rewrite_text`
- `detection_json`, `diff_json`
- `expires_at` (30일 후 자동 삭제)

**feedback**
- `run_id`, `user_id`, `type` (over_polish / under_polish / wrong_category / other), `comment`, `created_at`

## 7. 요금·쿼터·인증

| 플랜 | 가격 | 일 쿼터 | 글자 한도 | API |
|------|------|---------|----------|-----|
| Anonymous | 무료 | 5회 | 3,000자 | ✕ |
| Free (로그인) | 무료 | 30회 | 5,000자 | ✕ |
| Pro | $9/월 | 300회 | 10,000자 | ✓ (API 키 발급) |
| Team | $29/월 | 1,500회 | 20,000자 | ✓ + 웹훅 |

**BotID 검증**을 통해 익명 쿼터 남용을 차단. 쿼터는 Runtime Cache(IP + user hash)로 관리.

## 8. 배포·운영

- **환경**: `vercel.ts`로 설정 (vercel.json 사용 안 함).
- **환경변수**:
  - `AI_GATEWAY_API_KEY`
  - `DATABASE_URL` (Neon)
  - `CLERK_SECRET_KEY` (옵션)
  - `RESEND_API_KEY` (옵션)
- **Cron** (옵션): 일 1회 오래된 히스토리 정리 (`/api/cron/cleanup`).
- **모니터링**: Vercel Analytics + AI Gateway observability 대시보드.
- **Rolling Releases**로 신규 프롬프트 버전 점진 롤아웃.

## 9. 확장 로드맵

| 단계 | 내용 |
|------|------|
| **v0 MVP** | 익명·단일 호출·결과 저장 안 함. Phase 3까지만 (탐지+윤문+단일 검증) |
| **v1** | Clerk 로그인·히스토리·장르 프리셋·교차 검증 옵션 |
| **v2** | Pro/Team 플랜·API 키·웹훅·팀 계정 |
| **v3** | Chrome Extension — 선택 영역 즉석 윤문·Google Docs 플러그인 |
| **v4** | 한국어 외 일본어·중국어로 확장 (언어별 taxonomy 분리) |

## 10. 리스크 & 완화

- **악용(AI Detector 우회)**: 학계·저널리즘 맥락에서 논란. 서비스 설명에 "진실성 보증 도구 아님" 명시, 학술 제출용 사용을 약관에서 제한.
- **저작권**: 입력 본문 저장 기본 OFF. 저장 시 TTL 30일.
- **오탐·과윤문**: 등급 C/D일 때 "사람 검토 권고" 안내, 결과를 자동 게시하지 않음.
- **프롬프트 주입**: 입력을 역할·시스템 프롬프트로 해석하지 않도록 격리. Claude·GPT 모두 user 메시지 슬롯에서만 처리.
