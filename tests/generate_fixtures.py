"""fixture 재생성 — 살아있는 스킬로 output_text를 다시 뽑아 fixtures.json에 채운다.

얼린 fixture(test_humanize_e2e.py)는 스킬이 바뀌면 낡는다. 새 스킬 버전이 나오면
이 스크립트로 output_text를 refresh 한 뒤 커밋하면, 얼린 회귀 테스트가 최신 스킬 기준이 된다.

사용:
    python3 generate_fixtures.py                 # output_text 없는(null) fixture만 생성
    python3 generate_fixtures.py --all           # 전체 재생성(덮어씀)
    python3 generate_fixtures.py fx_b_heavy ...   # 특정 id만
    python3 generate_fixtures.py --dry-run --all  # 파일 안 쓰고 결과만 출력

`claude` CLI 필요(구독 인증). 비결정적이라 생성 후 변경률/시그널을 사람이 한 번 확인 권장.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import humanize_asserts as ha  # noqa: E402
import humanize_runner as hr  # noqa: E402

_PATH = os.path.join(_HERE, "fixtures.json")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="humanize fixture output_text 재생성")
    ap.add_argument("ids", nargs="*", help="대상 fixture id (없으면 규칙에 따름)")
    ap.add_argument("--all", action="store_true", help="output 있어도 전부 재생성")
    ap.add_argument("--dry-run", action="store_true", help="파일 안 쓰고 출력만")
    ap.add_argument("--strict", action="store_true", help="strict 파이프라인으로 생성")
    args = ap.parse_args(argv)

    if hr.CLAUDE_BIN is None:
        print("ERROR: claude CLI 없음 — 생성 불가", file=sys.stderr)
        return 2

    with open(_PATH, encoding="utf-8") as f:
        manifest = json.load(f)

    changed = 0
    for fx in manifest["fixtures"]:
        fid = fx["id"]
        if args.ids and fid not in args.ids:
            continue
        if not args.ids and not args.all and fx.get("output_text"):
            continue  # 기본: null 만
        try:
            out = hr.run_humanize(fx["input_text"], strict=args.strict)
        except hr.SkillUnavailable as exc:
            print(f"[{fid}] 실패: {exc}", file=sys.stderr)
            continue
        cr = ha.change_rate(fx["input_text"], out)
        print(f"[{fid}] 생성 · 변경률 {cr:.3f} · register {ha.register_of(out)}")
        print(f"    {out}")
        fx["output_text"] = out
        changed += 1

    if args.dry_run:
        print(f"\n[dry-run] {changed}건 생성(파일 미기록)")
        return 0
    if changed:
        with open(_PATH, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
            f.write("\n")
    print(f"\n{changed}건 갱신 -> {_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
