"""metrics_v2.py import-path 회귀 테스트.

metrics_v2 는 v1.6 metrics.py 를 sibling import 한다. 과거 이 경로가 스테이징
위치(`_workspace/…/03_metrics`) 기준으로 계산돼 references/ 로 옮긴 뒤엔
`.claude/.claude/…` 로 깨져 있었고, references/ 가 이미 sys.path 에 있을 때만
우연히 import 되던 잠재 버그였다.

이 테스트는 references/ 를 sys.path 에 넣지 않고 metrics_v2.py 를 **파일 경로로
직접 로드**해, v2 가 스스로 sibling metrics.py 를 찾는지 검증한다. (버그가 살아
있으면 서브프로세스가 ModuleNotFoundError 로 죽어 테스트 실패.)
"""
from __future__ import annotations

import os
import subprocess
import sys
import textwrap
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
_V2 = os.path.join(
    _REPO_ROOT, ".claude", "skills", "humanize-korean", "references", "metrics_v2.py"
)


class MetricsV2ImportTests(unittest.TestCase):
    def test_v2_self_resolves_v1_metrics(self) -> None:
        # cwd 를 레포 루트로 둬서 cwd-on-path 로도 references/ 가 안 잡히게 한다.
        # 따라서 `import metrics` 가 되려면 metrics_v2 가 스스로 자기 디렉터리를
        # sys.path 에 넣어야만 한다 (= 이 회귀 테스트가 지키려는 동작).
        code = textwrap.dedent(
            f"""
            import importlib.util
            spec = importlib.util.spec_from_file_location("metrics_v2_probe", {_V2!r})
            m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(m)
            assert m.VERSION == "v2.0", m.VERSION
            assert m.conclusion_pivot_count("결론적으로 그러므로") == 2   # 재export된 v1 함수
            assert m.double_passive_count("잊혀진 사실이 되어진다") >= 1  # v2 신규 함수
            print("OK")
            """
        )
        proc = subprocess.run(
            [sys.executable, "-c", code],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, f"metrics_v2 self-import 실패:\n{proc.stderr}")
        self.assertIn("OK", proc.stdout)


if __name__ == "__main__":
    unittest.main()
