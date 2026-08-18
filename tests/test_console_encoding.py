"""Windows(cp949) 콘솔에서 게이트가 죽지 않는지 검증 (#84).

## 배경

한국어 Windows 콘솔 기본 인코딩은 cp949 다. 게이트는 stdout 에 한글과
em-dash(U+2014)를 찍는데 cp949 는 U+2014 를 인코딩하지 못해 **첫 print 에서
UnicodeEncodeError 로 즉사**했다.

더 위험한 건 exit code 다. 파이썬은 미처리 예외에서 exit 1 로 끝나는데,
게이트 계약에서 1 은 "경고(변경률 30~50%)" 다. 즉 **검증이 죽었는데 경고로
읽힌다.** 검증 실패가 정상 판정으로 둔갑하는 것이 이 저장소가 가장 경계하는
실패 형태다(#59 의 "조용히 한 축이 죽는다"와 같은 계열).

이 테스트는 `PYTHONIOENCODING=cp949` 로 그 환경을 실제로 재현한다.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS = _ROOT / "scripts"

BEFORE = "원문은 이러하다. 수치는 1,200명이다."
AFTER = "원문은 이렇다. 수치는 1,200명이다."


def _cp949_env() -> dict:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "cp949"
    return env


class ConsoleEncodingTests(unittest.TestCase):
    def test_verify_gates_survives_cp949(self) -> None:
        """cp949 콘솔에서도 게이트 전 축이 출력되고 정상 종료해야 한다."""
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "b.txt").write_text(BEFORE, encoding="utf-8")
            (d / "a.txt").write_text(AFTER, encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(_SCRIPTS / "verify_gates.py"),
                 "--before", str(d / "b.txt"), "--after", str(d / "a.txt")],
                capture_output=True, text=True, env=_cp949_env(), timeout=120,
            )
        self.assertNotIn("UnicodeEncodeError", proc.stderr)
        self.assertIn("[P0", proc.stdout)
        self.assertIn("[P3 golden]", proc.stdout, "golden 축이 출력돼야 함")
        self.assertIn(proc.returncode, (0, 1, 2), f"예상치 못한 종료 {proc.returncode}")

    def test_missing_input_exits_3_not_1(self) -> None:
        """실행 오류는 exit 3 — 경고(1)와 반드시 구분돼야 한다."""
        proc = subprocess.run(
            [sys.executable, str(_SCRIPTS / "verify_gates.py"),
             "--before", "/nonexistent/b.txt", "--after", "/nonexistent/a.txt"],
            capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(proc.returncode, 3, "입력 부재는 3(실행 오류)이어야 함")

    def test_run_gate_maps_exception_to_3(self) -> None:
        """미처리 예외가 exit 1(경고)로 새지 않아야 한다 — 이게 핵심 회귀다."""
        sys.path.insert(0, str(_SCRIPTS))
        import console  # noqa: PLC0415

        def boom() -> int:
            raise RuntimeError("시뮬레이션")

        self.assertEqual(console.run_gate(boom), 3)

    def test_all_korean_printing_scripts_are_hardened(self) -> None:
        """한글을 찍는 런타임 스크립트는 전부 콘솔 하드닝을 걸어야 한다."""
        targets = [
            "verify_gates.py", "verify_change_rate.py", "prepare_monolith_input.py",
            "reassemble_chunks.py", "checks.py", "build_quick_rules.py",
            "build_diagnosis_rules.py", "sanitize_text.py",
        ]
        missing = []
        for name in targets:
            p = _SCRIPTS / name
            if not p.is_file():
                continue
            if "_console" not in p.read_text(encoding="utf-8"):
                missing.append(name)
        self.assertEqual(missing, [], f"콘솔 하드닝 누락: {missing}")


if __name__ == "__main__":
    unittest.main()


class SkillRootDerivationTests(unittest.TestCase):
    """SKILL.md 의 SKILL_ROOT 유도가 심링크·플러그인 양쪽에서 성립하는지 (#84-①).

    scripts/ 는 설치 루트에 있고 cwd 는 사용자 작업 디렉터리다. 마켓플레이스
    설치에서 둘은 절대 일치하지 않아, cwd 상대경로 호출은 항상 실패했다.
    """

    # 고정 횟수가 아니라 `.claude-plugin/` 마커를 만날 때까지 거슬러 올라간다.
    # 스킬 위치가 배포 방식마다 다를 수 있어(플러그인 루트 skills/ vs 그 밖),
    # 고정 깊이는 레이아웃이 바뀌면 조용히 엉뚱한 곳을 가리킨다.
    DERIVE = (
        'd="$(cd -P "$CLAUDE_SKILL_DIR" && pwd)"; '
        'while [ "$d" != / ] && [ ! -d "$d/.claude-plugin" ]; do d="$(dirname "$d")"; done; '
        'echo "$d"'
    )

    def _derive(self, skill_dir: Path) -> str:
        proc = subprocess.run(
            ["bash", "-c", self.DERIVE],
            capture_output=True, text=True,
            env={**os.environ, "CLAUDE_SKILL_DIR": str(skill_dir)}, timeout=30,
        )
        return proc.stdout.strip()

    def test_derivation_works_for_plugin_layout(self) -> None:
        """복사·플러그인 설치(실디렉터리) 레이아웃."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "install-root"
            (root / ".claude-plugin").mkdir(parents=True)
            (root / "skills" / "humanize-korean").mkdir(parents=True)
            (root / "scripts").mkdir()
            (root / "scripts" / "prepare_monolith_input.py").touch()
            got = self._derive(root / "skills" / "humanize-korean")
            self.assertTrue(
                (Path(got) / "scripts" / "prepare_monolith_input.py").is_file(),
                f"플러그인 레이아웃에서 유도 실패: {got}",
            )

    def test_derivation_works_for_symlink_install(self) -> None:
        """심링크 설치 — `cd -P` 없이는 홈 디렉터리로 올라가 실패하던 케이스."""
        with tempfile.TemporaryDirectory() as td:
            home = Path(td) / "home"
            (home / "skills").mkdir(parents=True)
            link = home / "skills" / "humanize-korean"
            link.symlink_to(_ROOT / "skills" / "humanize-korean")
            got = self._derive(link)
            self.assertEqual(
                Path(got).resolve(), _ROOT.resolve(),
                f"심링크 설치에서 유도 실패: {got} (cd -P 누락 의심)",
            )

    def test_skill_md_uses_absolute_script_paths(self) -> None:
        """SKILL.md 에 cwd 상대 `python3 scripts/` 호출이 남아 있으면 안 된다."""
        skill = (_ROOT / "skills" / "humanize-korean" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertNotIn(
            "python3 scripts/", skill,
            "cwd 상대 스크립트 호출 잔존 — ${SKILL_ROOT}/scripts/ 를 써야 함",
        )
        self.assertIn("cd -P", skill, "심링크 안전 유도(cd -P)가 명시돼야 함")
