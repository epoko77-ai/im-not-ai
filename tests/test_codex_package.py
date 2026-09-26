"""Codex skill packaging and standalone-copy regression tests."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "codex" / "skills" / "humanize-korean"


class CodexPackageTests(unittest.TestCase):
    def assert_core_role_contracts(
        self, codex: str, claude: str, roles: dict[str, str]
    ) -> None:
        def section(title: str) -> str:
            return codex.split(f"## {title}\n", 1)[1].split("\n## ", 1)[0]

        for name in ("diagnostician", "monolith", "finalizer"):
            self.assertIn(f"references/roles/{name}.md", codex)

        diagnosis = roles["diagnostician"]
        self.assertIn("3~6개", diagnosis)
        self.assertIn("카운트가 0보다 큰 본진 ID", diagnosis)
        self.assertIn("diagnosis-rules.md", diagnosis)
        self.assertIn("02_diagnosis.md", diagnosis)
        self.assertIn("윤문하지 말고", diagnosis)

        monolith = roles["monolith"]
        self.assertIn("실제 span과 룰 ID", monolith)
        self.assertIn("D → A → I → G → H → F → B → C·J → E", monolith)
        self.assertIn("자체검증 6항", monolith)
        self.assertIn("위반 edit만 한 번 롤백", monolith)
        self.assertIn("청크 출력이면 summary 없이", monolith)
        self.assertIn("50% 변경에 임박하면 추가 편집을 멈춘다", monolith)

        finalizer = roles["finalizer"]
        self.assertIn("원문, 윤문본, 진단을 직접 대조", finalizer)
        self.assertIn("문제 구간만 국소 보정", finalizer)
        self.assertIn("final_pre_finalize.md", finalizer)
        self.assertIn("accept|corrected|hold_and_report", finalizer)
        self.assertIn("HUMANIZE-SUMMARY", finalizer)
        self.assertIn("정확히 하나 유지", finalizer)

        setup = section("실행 준비")
        self.assertIn("route_hint", setup)
        codex_route = next(line for line in setup.splitlines() if "`--strict`" in line)
        claude_route = claude.split("### 경로 결정 규칙\n", 1)[1].split("\n### ", 1)[0]
        claude_overrides = next(line for line in claude_route.splitlines() if "`--strict`" in line)
        self.assertIn(
            "`--strict`, `정밀 모드`, `정밀하게`, `제대로`는 heavy로",
            codex_route,
        )
        self.assertIn("`가볍게`, `빠르게만`은 light로", codex_route)
        self.assertIn(
            '`--strict`·"정밀 모드"·"정밀하게"·"제대로" → **heavy 고정**',
            claude_overrides,
        )
        self.assertIn('"가볍게"·"빠르게만" → **light 고정**', claude_overrides)
        self.assertIn("힌트가 없으면 standard", setup)
        self.assertIn("route_hint` 필드가 없거나", claude_route)
        self.assertIn("standard", claude_route)
        self.assertIn("30% 이상은 경고, 50% 이상은 결과 채택 금지", codex)

        light = section("Light")
        self.assertIn("진단 없이 monolith", light)
        self.assertIn("공통 게이트", light)
        standard = section("Standard")
        self.assertIn("diagnostician", standard)
        self.assertIn("15,000자 이하는 임의로 청킹하지 않는다", standard)
        self.assertIn("exit 1 또는 자체검증 2항 이상 실패면 finalizer로 승급", standard)
        heavy = section("Heavy")
        self.assertIn("2개 이상이면", heavy)
        self.assertIn("단일 청크에서도 이 단계를 생략하지 않는다", heavy)
        self.assertIn("공통 게이트 뒤 항상 finalizer", heavy)
        self.assertIn("finalize 뒤 공통 게이트를 다시 실행", heavy)

        gate = section("공통 게이트")
        self.assertIn("exit 0: 수렴", gate)
        self.assertIn("exit 1: 경고 축을 밝히고 finalizer로 승급", gate)
        self.assertIn("exit 2: 결과 채택 금지", gate)
        self.assertIn("안전본으로 되돌리고 monolith를 보수적으로 1회 재실행", gate)
        self.assertIn("재차 exit 2면 `hold_and_report`", gate)
        self.assertIn("exit 3: 실행 오류로 판정 불가", gate)
        self.assertIn("결과 채택과 finalizer 승급을 중단", gate)

        claude_gate = claude.split("## Phase 2.5: 구조 게이트", 1)[1].split("\n## ", 1)[0]
        warning_row = next(line for line in claude_gate.splitlines() if line.startswith("| 1 |"))
        abort_row = next(line for line in claude_gate.splitlines() if line.startswith("| 2 |"))
        self.assertIn("경고 — 문자율 30~50%", warning_row)
        self.assertIn("finalize 승급", warning_row)
        self.assertIn("중단 — 문자율 ≥ 50%", abort_row)
        self.assertIn("롤백 지시 후 1회 재실행", abort_row)
        self.assertIn("재차 2면 `hold_and_report`", abort_row)

    def test_core_role_contracts_stay_aligned(self) -> None:
        codex = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        claude = (ROOT / "skills" / "humanize-korean" / "SKILL.md").read_text(encoding="utf-8")
        role_dir = ROOT / "skills" / "humanize-korean" / "references" / "roles"
        roles = {}
        for name in ("diagnostician", "monolith", "finalizer"):
            source = role_dir / f"{name}.md"
            self.assertEqual((SKILL / "references" / "roles" / f"{name}.md").resolve(), source)
            roles[name] = source.read_text(encoding="utf-8")
        self.assert_core_role_contracts(codex, claude, roles)

        # Check that each source tree can drift independently and fail this contract.
        mutations = (
            ("diagnosis limit", codex, claude, {**roles, "diagnostician": roles["diagnostician"].replace("3~6개", "2~6개")}),
            ("monolith stop action", codex, claude, {**roles, "monolith": roles["monolith"].replace("추가 편집을 멈춘다", "추가 편집을 계속한다")}),
            ("standard chunk limit", codex.replace("15,000자 이하는", "12,000자 이하는"), claude, roles),
            ("gate error routing", codex.replace("결과 채택과 finalizer 승급을 중단", "finalizer로 승급"), claude, roles),
            ("gate abort rollback", codex.replace("안전본으로 되돌리고 monolith를 보수적으로 1회 재실행", "안전본을 버리고 재실행하지 않는다"), claude, roles),
            ("Codex heavy override", codex.replace("`--strict`, `정밀 모드`, `정밀하게`", "`--strict`, `정밀하게`"), claude, roles),
            ("shared heavy override", codex, claude.replace('"정밀 모드"·', ''), roles),
            ("shared gate abort threshold", codex, claude.replace("문자율 ≥ 50%", "문자율 ≥ 60%"), roles),
            ("Codex route destinations", codex.replace("`제대로`는 heavy로, `가볍게`, `빠르게만`은 light로", "`제대로`는 light로, `가볍게`, `빠르게만`은 heavy로"), claude, roles),
            ("shared route destinations", codex, claude.replace('→ **heavy 고정**. "가볍게"·"빠르게만" → **light 고정**', '→ **light 고정**. "가볍게"·"빠르게만" → **heavy 고정**'), roles),
            ("shared gate row thresholds", codex, claude.replace("| 1 | 경고 — 문자율 30~50%", "| 1 | 경고 — 문자율 ≥ 50%").replace("| 2 | 중단 — 문자율 ≥ 50%", "| 2 | 중단 — 문자율 30~50%"), roles),
        )
        for name, changed_codex, changed_claude, changed_roles in mutations:
            with self.subTest(mutation=name):
                with self.assertRaises(AssertionError):
                    self.assert_core_role_contracts(changed_codex, changed_claude, changed_roles)

    def test_required_package_files_exist(self) -> None:
        required = [
            "SKILL.md",
            "agents/openai.yaml",
            "scripts/prepare_monolith_input.py",
            "scripts/reassemble_chunks.py",
            "scripts/verify_change_rate.py",
            "scripts/verify_gates.py",
            "references/quick-rules.md",
            "references/diagnosis-rules.md",
            "references/roles/diagnostician.md",
            "references/roles/monolith.md",
            "references/roles/finalizer.md",
        ]
        for relative in required:
            self.assertTrue((SKILL / relative).is_file(), relative)

        contract = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("단일 청크에서도 이 단계를 생략하지 않는다", contract)
        self.assertIn("summary가 없으므로 finalizer", contract)
        self.assertIn('SKILL_ROOT="$(cd -P', contract)
        self.assertNotIn("$SKILL_DIR/scripts/", contract)
        self.assertGreaterEqual(contract.count("${SKILL_ROOT}/scripts/"), 5)

    def test_source_wrapper_runs_from_foreign_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td) / "run"
            run_dir.mkdir()
            (run_dir / "01_input.txt").write_text("테스트 문장입니다.", encoding="utf-8")
            subprocess.run(
                [
                    sys.executable,
                    str(SKILL / "scripts" / "prepare_monolith_input.py"),
                    "--run-dir",
                    str(run_dir),
                    "--genre",
                    "essay",
                ],
                cwd=td,
                check=True,
                capture_output=True,
                text=True,
            )
            metrics = json.loads((run_dir / "00_metrics.json").read_text(encoding="utf-8"))
            self.assertIn(metrics["route_hint"], {"light", "standard", "heavy"})

    def test_copy_install_is_self_contained(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fake_home = Path(td) / "home"
            codex_home = fake_home / ".codex"
            codex_home.mkdir(parents=True)
            env = os.environ.copy()
            env.update({"HOME": str(fake_home), "CODEX_HOME": str(codex_home)})
            subprocess.run(
                ["bash", str(ROOT / "install.sh"), "--codex-only", "--copy"],
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
            installed = codex_home / "skills" / "humanize-korean"
            self.assertFalse((installed / "references").is_symlink())
            self.assertIn("METRICS_DIR", (installed / "scripts" / "prepare_monolith_input.py").read_text())
            self.assertTrue((installed / "scripts" / "checks.py").is_file())
            self.assertTrue((installed / "scripts" / "console.py").is_file())
            run_dir = Path(td) / "outside" / "run"
            run_dir.mkdir(parents=True)
            before = "정부는 지원을 확대해야 한다. 통계는 매년 개선되고 있다."
            (run_dir / "01_input.txt").write_text(before, encoding="utf-8")
            subprocess.run(
                [
                    sys.executable,
                    str(installed / "scripts" / "prepare_monolith_input.py"),
                    "--run-dir",
                    str(run_dir),
                    "--genre",
                    "essay",
                ],
                cwd=run_dir.parent,
                check=True,
                capture_output=True,
                text=True,
            )
            for after, exit_code in (
                (before, 0),
                (before.replace("확대해야 한다", "확대한다"), 1),
            ):
                with self.subTest(after=after):
                    (run_dir / "final.md").write_text(after, encoding="utf-8")
                    gate = subprocess.run(
                        [
                            sys.executable,
                            str(installed / "scripts" / "verify_gates.py"),
                            "--before",
                            str(run_dir / "01_input.txt"),
                            "--after",
                            str(run_dir / "final.md"),
                            "--genre",
                            "essay",
                            "--json",
                        ],
                        cwd=run_dir.parent,
                        capture_output=True,
                        text=True,
                    )
                    self.assertEqual(gate.returncode, exit_code, gate.stdout + gate.stderr)
                    report = json.loads(gate.stdout[gate.stdout.index("{"):])
                    expected_losses = [] if exit_code == 0 else [{
                        "kind": "당위",
                        "before": "정부는 지원을 확대해야 한다.",
                        "after": "정부는 지원을 확대한다.",
                    }]
                    self.assertEqual(report["modality"]["lost_pairs"], expected_losses)
                    self.assertEqual(report["modality"]["uncertain_pairs"], [])

    def test_copy_install_backs_up_existing_symlink_outside_skills(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fake_home = Path(td) / "home"
            codex_home = fake_home / ".codex"
            installed = codex_home / "skills" / "humanize-korean"
            installed.parent.mkdir(parents=True)
            installed.symlink_to(SKILL)
            env = os.environ.copy()
            env.update({"HOME": str(fake_home), "CODEX_HOME": str(codex_home)})
            subprocess.run(
                ["bash", str(ROOT / "install.sh"), "--codex-only", "--copy"],
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertTrue(installed.is_dir())
            self.assertFalse(installed.is_symlink())
            self.assertEqual(list(installed.parent.glob("humanize-korean*")), [installed])
            backups = list((codex_home / "backups").glob("*/skills/humanize-korean"))
            self.assertEqual(len(backups), 1)
            self.assertTrue(backups[0].is_symlink())

    def test_copy_install_preserves_existing_skill_if_backup_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            codex_home = Path(td) / ".codex"
            installed = codex_home / "skills" / "humanize-korean"
            installed.parent.mkdir(parents=True)
            installed.symlink_to(SKILL)
            (codex_home / "backups").write_text("blocked", encoding="utf-8")
            env = os.environ.copy()
            env.update({"HOME": td, "CODEX_HOME": str(codex_home)})
            result = subprocess.run(
                ["bash", str(ROOT / "install.sh"), "--codex-only", "--copy"],
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(installed.is_symlink())
            self.assertEqual(installed.resolve(), SKILL.resolve())

    def test_force_install_backs_up_directory_outside_skills(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fake_home = Path(td) / "home"
            codex_home = fake_home / ".codex"
            installed = codex_home / "skills" / "humanize-korean"
            installed.mkdir(parents=True)
            (installed / "sentinel.txt").write_text("keep me", encoding="utf-8")
            env = os.environ.copy()
            env.update({"HOME": str(fake_home), "CODEX_HOME": str(codex_home)})
            subprocess.run(
                ["bash", str(ROOT / "install.sh"), "--codex-only", "--force"],
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertTrue(installed.is_symlink())
            self.assertEqual(list(installed.parent.glob("humanize-korean*")), [installed])
            backups = list((codex_home / "backups").glob("*/skills/humanize-korean"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(
                (backups[0] / "sentinel.txt").read_text(encoding="utf-8"), "keep me"
            )


if __name__ == "__main__":
    unittest.main()
