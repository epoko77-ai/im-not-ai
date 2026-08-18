# 골든 픽스처 — commit-ko 품질 회귀 게이트

`tests/golden/`(humanize-korean)와 같은 설계를 커밋 메시지 register로 축소한 버전입니다.
LLM 없이 순수 Python으로 "commit-ko가 하지 말아야 할 것"을 회귀 검증합니다.
모든 픽스처는 합성 커밋 메시지이며, 이슈 번호·이메일·경로는 전부 허구입니다.

## 구조

```
tests/golden_commit/
├── commit_checks.py           # 결정적 채점기 (stdlib only)
├── fixtures/
│   └── <NN_실패모드-이름>/
│       ├── input.txt              # 윤문 전 커밋 메시지 원문
│       ├── bad_output.txt         # 실패 사례 재현 (채점기가 반드시 FAIL시켜야 함)
│       ├── good_output.txt        # 기대 수준의 정상 윤문 (반드시 PASS해야 함)
│       └── expected_failures.json # bad가 트리거해야 할 실패 코드 목록
└── README.md
tests/test_golden_commit.py    # pytest / unittest 겸용
```

## commit-msg 훅 (opt-in)

`scripts/commit_msg_lint.py`는 이 골든 게이트와 같은 lexicon(§1~5)을 정규식으로
직접 실행 가능하게 파생시킨 것으로, 실제 커밋 시점에 경고만 띄운다(차단 없음).
저장소에 `.githooks/commit-msg`로 커밋되어 있지만 기본으로 켜져 있지는 않다 —
저장소별로 한 번 옵트인해야 한다:

```bash
git config core.hooksPath .githooks   # 활성화
git config --unset core.hooksPath      # 비활성화
```

건너뛰기(옵트인 상태에서): 커밋 메시지에 `[skip-commit-ko]` 포함, 또는
`COMMIT_KO_HOOK_SKIP=1 git commit ...`. Merge·Revert·fixup!·squash! 커밋은
자동으로 건너뛴다.

## 실행

```bash
# 전체 (pytest 또는 unittest)
pytest tests/test_golden_commit.py
python3 -m unittest tests.test_golden_commit

# 채점기 단독 — 실제 윤문 결과를 게이트에 통과시킬 때
python3 tests/golden_commit/commit_checks.py fixtures/01_prefix_altered/input.txt <윤문결과.txt>
```

## 설계 원칙 — 방향성 게이트

humanize-korean의 골든셋과 동일하게, "정확히 이 문자열"이 아니라
**"이 요소가 사라지면/이 카운트가 늘면 실패"** 방향 조건만 씁니다.

- Conventional Commits `type(scope)!:` 접두사가 원문과 달라지면 FAIL (`prefix_altered`)
- `Co-authored-by:`·`Closes #N` 같은 git 트레일러가 사라지거나 값이 바뀌면 FAIL
  (`trailer_lost`·`trailer_altered`)
- 백틱 코드 스팬(파일·함수명)이 원문 그대로 없으면 FAIL (`code_span_altered`)
- `하였` 계열이 원문보다 **늘면** FAIL — 과공손 상향 주입 (`hayeot_injection`,
  SKILL.md 철칙 #3)
- 사무적 격식 동사(수행/진행/실시)가 원문보다 **늘면** FAIL — commit-ko 존재
  이유에 반하는 역주행 (`bureaucratic_injection`)
- 원문에 없던 수치(이슈 번호 포함)가 새로 등장하면 FAIL (`number_injected`)

오탐을 극도로 경계합니다. Conventional Commits 형식이 아닌 메시지는 접두사
체크 자체를 건너뛰고, 트레일러가 없는 메시지는 트레일러 체크를 건너뜁니다.

## 못 잡는 것 (정직한 한계)

- 의미 드리프트(원문에 없던 이유·효과를 지어내는 것) — regex로 판정 불가
- 사무적 어휘가 남아 있는데 못 지운 경우 (이건 "실패"가 아니라 "미개선"이라
  방향성 게이트 철학상 gate하지 않음 — good_output이 PASS하는 것으로 개선
  여지를 보여줄 뿐)
- body 문단 내 자연스러움(어색한 직역투 잔존 등) — humanize-korean처럼 산문
  분량이 크지 않아 별도 채점기를 두지 않음

## 픽스처 추가하는 법

1. `fixtures/NN_실패모드-이름/` 디렉토리를 만듭니다.
2. `input.txt` — 실패 모드를 선명하게 유발하는 합성 커밋 메시지.
3. `bad_output.txt` — 그 실패가 실제로 일어난 모습.
4. `good_output.txt` — SKILL.md 철칙(의미·범위·타입 불변, 새 내용 삽입 금지,
   과공손 방향 금지)을 지킨 정상 윤문.
5. `expected_failures.json` — `{"description": "...", "bad_must_fail": [코드들]}`.
   코드 목록은 `commit_checks.py` 상단 docstring 참조.
6. `python3 -m unittest tests.test_golden_commit`이 통과하는지 확인합니다.
   새 실패 모드가 기존 체크로 안 잡히면 `checks.py`에 방향성 체크를 추가하되,
   반드시 무변경(identity)·정상 윤문이 PASS함을 함께 증명하세요.
