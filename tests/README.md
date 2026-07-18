# tests — humanize-korean 회귀 테스트

LLM 기반 윤문 스킬은 출력이 비결정적이라 "골든 출력 문자열 비교"가 불가능하다.
그래서 문자열 정답 대신 **불변식 · 변경률 밴드 · metrics 시그널 델타**로 판정하고,
스킬을 실제로 실행하느냐에 따라 3계층으로 나눈다.

## 계층

| 파일 | 계층 | claude 필요 | 무엇을 잡나 |
|---|---|:---:|---|
| `test_humanize_asserts.py` | 1. 단위 | ✗ | 판정 헬퍼(`humanize_asserts.py`) 로직 |
| `test_humanize_e2e.py` | 2. 얼린 fixture | ✗ | 오프라인 스모크·골든 스냅샷 |
| `test_humanize_live.py` | 3. live 통합 | ✓ | **실제 스킬 회귀** |

- `humanize_asserts.py` — 순수 판정 함수(change_rate·fidelity·register·metrics 시그널). stdlib only.
- `humanize_runner.py` — `claude -p`로 스킬 실행(Claude Code 구독 인증, 별도 API 키 불필요).
- `fixtures.json` — (입력, 얼린 출력, 판정 기준) 데이터 + LLM-judge 루브릭.
- `generate_fixtures.py` — 스킬로 출력 재생성.

## 실행

```
cd tests
python3 -m unittest test_humanize_asserts test_humanize_e2e          # 오프라인, 빠름 (claude 무)
python3 -m unittest test_humanize_live                              # 살아있는 스킬 (claude 필요, 느림)
HUMANIZE_LIVE_IDS=fx_b_heavy python3 -m unittest test_humanize_live  # 부분 실행
HUMANIZE_LIVE_K=3 python3 -m unittest test_humanize_live            # 반복(flaky 탐지)
```
계층3은 `claude` CLI 없으면 자동 skip → 크레덴셜 없는 CI에서도 안전.

## 판정 차원

- **T1 의미 불변** — `protected_tokens`(고유명사·수치·리터럴 인용)가 출력에 100% 생존.
- **T2 용량-반응** — `change_rate`가 fixture 티어별 밴드 안 (사람 글 ≈0, 헤비 AI 큰 값).
- **T3 과윤문 가드** — `change_rate` ≤ max(예: 0.50). 스킬의 강제중단 가드 검증.
- **T6 패턴 재현율** — `signal_drop`: 심은 패턴의 metrics 시그널이 기준 이상 하락.

## fixture 추가

`fixtures.json`의 `fixtures[]`에 항목을 추가한다:
```json
{
  "id": "fx_example",
  "protected_tokens": ["고유명사", "42"],
  "change_rate": {"min": 0.0, "max": 0.5},
  "signal_drop": {"name": "conclusion_pivot_count", "min_drop": 2},
  "register": "합니다",
  "input_text": "...",
  "output_text": null
}
```
- `output_text`가 `null`이면 계층2는 그 fixture를 skip한다. 채우려면
  `python3 generate_fixtures.py fx_example` (스킬로 생성) 실행 후 결과를 검토하고 커밋.
- `protected_tokens`는 **하드 불변식만** 넣는다 — 재구성 가능한 내용 문구가 아니라
  이름·수치·리터럴 인용처럼 반드시 보존돼야 하는 것.

## 스킬 버전업 시

스킬/룰이 바뀌면 얼린 fixture가 낡는다. 다음으로 최신 기준에 맞춘다:
```
python3 generate_fixtures.py --all        # output_text 전체 재생성
python3 -m unittest test_humanize_live    # 새 스킬로 live 검증
```
