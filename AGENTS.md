# AGENTS.md — Codex 세션용 에이전트 컨텍스트

이 파일은 Codex 세션의 진입점이다. Codex는 저장소 루트의 `AGENTS.md`를 관례 경로로 읽는다.

## 공통 가이드

작업 전 `CLAUDE.md`를 읽는다. 프로젝트 개요, 철칙, 워터마킹 입장, 파이프라인,
심각도·품질 등급, 금기, 릴리스 절차는 `CLAUDE.md`를 따르며 이 파일에 복제하지 않는다.
단, `CLAUDE.md`의 Claude Code 도구명·서브에이전트(`agents/*.md`) 서술은 Claude 런타임
기준이다. Codex 세션의 실행 절차는 아래 진입점이 우선한다.

## Codex 고유 사항

- **런타임 주체**: Claude 서브에이전트 대신 Codex가
  `skills/humanize-korean/references/roles/`의 역할 계약을 협업 에이전트 또는
  순차 폴백으로 실행한다.
- **진입점**: `codex/skills/humanize-korean/SKILL.md`. 참조 자료는 같은 폴더의
  `references`(→ `skills/humanize-korean/references` 링크)를, 공용 스크립트는
  `scripts/` 래퍼(루트 `scripts/` 실행)를 통한다.
- **테스트·빌드** (CI `.github/workflows/test.yml`과 동일):
  ```bash
  pip install pytest
  pytest tests/ -v
  python3 scripts/build_quick_rules.py --check
  python3 scripts/build_diagnosis_rules.py --check
  bash tests/test_install_flags.sh
  bash tests/test_install_smoke.sh
  ```
  taxonomy를 고쳤으면 두 build 스크립트를 `--check` 없이 실행해 생성 파일을 갱신한다.
  Codex 패키지 계약은 `tests/test_codex_package.py`가 검사한다.
