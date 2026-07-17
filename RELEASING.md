# RELEASING — 릴리스 체크리스트

v1.6.1과 v2.0 릴리스에서 `SKILL.md` 버전 갱신이 **두 번 연속 누락**됐고, 그 결과 clone한 사용자가 v2.0 표기 아래 v1.5 오케스트레이션을 실행하는 사고가 있었습니다. 또 태그 `v2.0.0`이 발행 노트·썸네일 커밋보다 먼저 찍혀 릴리스 아카이브에 v2.0 발행 노트가 빠졌습니다. 본 문서는 그 두 사고의 재발을 구조적으로 막는 체크리스트입니다.

## 1. 버전 문자열이 등장하는 위치 (전수 — 릴리스마다 모두 갱신)

grep 전수 조사(2026-07-17, v2.0.1 기준)로 확정한 목록입니다.

| # | 파일 | 위치 | 형식 |
|---|------|------|------|
| 1 | `.claude/skills/humanize-korean/SKILL.md` | frontmatter `version:` | `"X.Y.Z"` — **런타임 SSOT. 여기가 누락되면 사용자는 구버전을 실행합니다** |
| 2 | `.claude/skills/humanize-korean/SKILL.md` | 제목(H1) + 상단 "버전 요약" 블록 | `vX.Y` |
| 3 | `.claude/skills/humanize-korean/SKILL.md` | Phase 0 런타임 배너 (`humanize-korean vX.Y — {fast\|strict} 모드 …`) | `vX.Y` — 실행 시 사용자에게 그대로 출력됨 |
| 4 | `README.md` | 제목(H1) + "아키텍처" 헤더 | `vX.Y.Z` / `vX.Y` |
| 5 | `README.md` | 신규 릴리스 노트 절 (`## vX.Y — …`) | 절 추가 |
| 6 | `CLAUDE.md` | 제목(H1) | `vX.Y.Z` |
| 7 | `.claude/commands/humanize.md` | 배너 예시 (`humanize-korean vX.Y — strict 모드 …`) | `vX.Y` |
| 8 | `references/ai-tell-taxonomy.md` | 제목(H1) + "버전 관리" 절 | 분류 체계 버전 — 스킬 버전과 **별개 트랙**. 분류 변경이 있는 릴리스에서만 갱신 |
| 9 | `references/quick-rules.md` | 제목(H1) | 분류 체계 버전 트랙과 동행 |
| 10 | git tag | `vX.Y.Z` | 아래 §3 시점 규칙 준수 |

**갱신 불필요 (도입 시점 표기)**: `scripts/prepare_monolith_input.py` docstring의 "v1.6", `.claude/agents/humanize-monolith.md` description의 "v1.6.1", README의 과거 릴리스 노트 절 — 모두 그 기능이 도입된 버전의 역사 기록이므로 건드리지 않습니다. 단, **에이전트의 동작 계약(도구 호출 캡·산출물 형태)이 바뀌는 릴리스라면** 해당 에이전트 정의의 description도 함께 갱신합니다.

전수 확인 명령 (릴리스 브랜치에서 실행, 구버전 표기 잔존 여부 검사):

```bash
grep -rn "v[0-9]\.[0-9]" \
  .claude/skills/humanize-korean/SKILL.md \
  .claude/commands/ CLAUDE.md \
  | grep -v "역사\|이력\|변경 고지\|버전 요약"
# README.md는 과거 릴리스 노트가 많으므로 제목·아키텍처 헤더만 육안 확인:
sed -n '1,40p' README.md
```

## 2. 릴리스 전 확인 항목

- [ ] **글로벌 에이전트 심링크 동기화** (에이전트를 추가·은퇴한 릴리스만): `~/.claude/agents/`는 프로젝트 `.claude/agents/*.md`로의 파일별 심링크다. 신규 에이전트는 `ln -sf`로 링크를 걸고, 은퇴한 에이전트는 죽은 링크를 `rm`한다. 링크가 없으면 세션이 그 에이전트를 로드하지 못한다(정밀 3콜이 안 돎). 확인: `ls -la ~/.claude/agents/ | grep humanize`로 링크 대상이 실재 파일인지 검사.


- [ ] **테스트**: `python3 -m pytest tests/ -q` 전체 통과 (pytest 미설치 환경이면 `pip install pytest` 후 실행)
- [ ] **shim 스모크**: `python3 scripts/prepare_monolith_input.py --text "테스트 문장입니다." --genre essay` 가 `00_metrics.json` + `01_input_with_metrics.txt`를 만드는지 확인 (생성된 임시 run 디렉토리는 삭제)
- [ ] **버전 문자열**: §1 표의 #1~#9 전수 갱신 — 특히 **SKILL.md frontmatter·배너** (과거 2회 누락 지점)
- [ ] **문서 정합**: 도구 호출 캡·산출물 목록(fast=`final.md` 1개, strict=`final.md`+`summary.md`)이 SKILL.md·README·CLAUDE.md·에이전트 정의에서 일치하는지
- [ ] **발행 노트**: README에 `## vX.Y` 절 작성, 검증 결과는 실측 수치만 (추정 금지)
- [ ] **부속물**: 썸네일·social preview 갱신이 있으면 태그 전에 머지

## 3. 태그를 언제 찍는가

**규칙: 태그는 해당 릴리스의 모든 커밋(발행 노트·썸네일·문서 포함)이 main에 머지된 뒤, main의 머지 커밋에 찍는다.**

- 과거 사고: `v2.0.0` 태그가 main보다 8커밋 뒤에 머물러(PR #20~#23 발행 노트·썸네일이 태그 이후 머지), GitHub 릴리스 아카이브(zip/tarball)에 v2.0 발행 노트가 없습니다.
- 이미 공개된 태그는 이동하지 않습니다(clone 이력 오염). 대신 다음 패치 태그(`v2.0.1`)를 규칙대로 찍어 아카이브를 정상화합니다.
- 태그 후 GitHub Release를 생성하고 README 발행 노트 절을 본문으로 사용합니다.

## 4. 순서 요약

1. 릴리스 브랜치에서 §1 버전 문자열 전수 갱신 + §2 체크리스트 통과
2. PR → 리뷰 → main 머지 (발행 노트·부속물 포함 전부)
3. main에서 `git tag vX.Y.Z && git push origin vX.Y.Z`
4. GitHub Release 생성
