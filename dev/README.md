# dev/ — 릴리스 회차용 개발 자산 (플러그인 로더 범위 밖)

## dev/agents/ — 개발용 에이전트 5종

v2.0 학술 흡수 회차 전용 도구다. 윤문 런타임(`skills/humanize-korean`)은 호출하지 않는다.

| 에이전트 | 용도 |
|---|---|
| translationese-research-distiller | 번역투 학술 보고서 구조화 증류 |
| korean-translation-scholar | 학술 인용 계보를 taxonomy + scholarship.md 양면 안착 |
| taxonomy-gap-analyzer | 외부 후보 풀 vs 본진 3축 갭 매핑 |
| post-editese-metric-engineer | post-editese 3축을 metrics_v2.py로 코드화 |
| quick-rules-integrator | 변경 묶음의 quick-rules 안착 + 캡 회귀 검증 + PR 준비 |

**왜 루트 `agents/`가 아닌가.** Claude Code 플러그인 로더는 루트 `agents/*.md`를 전부 세션 에이전트 목록에 올리고, 그 설명문은 설치 사용자의 매 세션 컨텍스트에 실린다. 윤문과 무관한 정의가 전역 풀에 있으면 토큰을 쓰고 description 매칭으로 잘못 호출될 수도 있다(`install.sh`가 기본 설치에서 이 5종을 빼는 이유와 같다). 로더 범위 밖에 두면 두 문제가 함께 사라진다.

**쓰는 방법.** 기여자 기기에서만 `./install.sh --all-agents`로 함께 연결하거나, 필요한 정의를 `Agent` 도구에 직접 지정한다. 런타임 3종·유지보수 1종은 루트 `agents/`에 그대로 있다(`tests/test_agent_inventory.py`가 두 폴더의 구성을 고정한다). `dev/agents/`에는 에이전트 정의(.md)만 둔다 — `--all-agents`가 폴더의 .md 전부를 링크하기 때문이다.
