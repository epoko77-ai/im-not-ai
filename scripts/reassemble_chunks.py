#!/usr/bin/env python3
"""Humanize KR v2.0.1 — 청크 윤문 결과 재조립기.

`prepare_monolith_input.py --chunk` 가 만든 chunk_manifest.json 순서대로
청크별 윤문 결과(02_chunk_{NN}_rewritten.txt)를 병합해 03_reassembled.md 를
만든다. passthrough 청크(문서 말미 각주 블록)는 원문 그대로 삽입한다.

안전장치:
  - manifest 의 source_sha256 과 현재 01_input.txt 대조 — 청킹 이후 입력이
    바뀌었으면 낡은 경계로 재조립하는 사고를 막기 위해 중단.
  - manifest 구간 연결이 원문과 일치하는지 lossless 재검증.
  - 청크별 문자 수 대사: 윤문 결과가 원문 절반 이하(유실 의심)거나 2배
    초과(증식 의심)면 경고. --strict 면 경고를 오류(exit 1)로 처리.
  - 윤문 결과가 비어 있으면 즉시 오류.

공백 복원: 청크 경계의 문단 구분 개행은 분할 시 앞 청크 꼬리에 붙어 있다.
LLM 출력은 앞뒤 공백이 불안정하므로, 윤문 결과의 앞뒤 공백을 벗겨내고
원문 청크의 leading/trailing 공백을 그대로 재부착한다. 이 규칙 덕에
"윤문 없이 원문 그대로"를 청크 결과로 쓰면 재조립 = 원문 (왕복 항등).

stdlib only. LLM 개입 0, 100% 결정적.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def _leading_ws(s: str) -> str:
    return s[: len(s) - len(s.lstrip())]


def _trailing_ws(s: str) -> str:
    return s[len(s.rstrip()) :]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Humanize KR chunk reassembler")
    p.add_argument("--run-dir", required=True, help="chunk_manifest.json 이 있는 런 디렉토리")
    p.add_argument("--output", default="03_reassembled.md", help="병합 결과 파일명")
    p.add_argument(
        "--report", default="03_reassembly_report.json", help="문자 수 대사 리포트 파일명"
    )
    p.add_argument(
        "--strict", action="store_true", help="문자 수 대사 경고를 오류(exit 1)로 처리"
    )
    args = p.parse_args(argv)

    run_dir = Path(args.run_dir)
    manifest_path = run_dir / "chunk_manifest.json"
    if not manifest_path.exists():
        raise SystemExit(
            f"chunk_manifest.json not found in {run_dir}; "
            "run prepare_monolith_input.py --chunk first"
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    source_path = run_dir / manifest["source_file"]
    if not source_path.exists():
        raise SystemExit(f"source file not found: {source_path}")
    text = source_path.read_text(encoding="utf-8")

    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if sha != manifest.get("source_sha256"):
        raise SystemExit(
            "입력이 청킹 이후 변경됨 (sha256 불일치) — "
            "prepare_monolith_input.py --chunk 재실행 필요"
        )

    chunks = manifest["chunks"]
    joined = "".join(text[c["start"] : c["end"]] for c in chunks)
    if joined != text:
        raise SystemExit(
            "manifest 구간 연결이 원문과 불일치 — manifest 손상, --chunk 재실행 필요"
        )

    missing = [
        c["rewritten_file"]
        for c in chunks
        if not c["passthrough"] and not (run_dir / c["rewritten_file"]).exists()
    ]
    if missing:
        raise SystemExit(
            f"윤문 결과 파일 누락 {len(missing)}건: {', '.join(missing)}"
        )

    pieces: list[str] = []
    report_chunks: list[dict] = []
    warnings: list[str] = []
    for c in chunks:
        orig = text[c["start"] : c["end"]]
        idx = c["index"]
        if c["passthrough"]:
            pieces.append(orig)
            report_chunks.append(
                {"index": idx, "passthrough": True, "orig_chars": len(orig)}
            )
            continue

        rewritten = (run_dir / c["rewritten_file"]).read_text(encoding="utf-8")
        core_orig = orig.strip()
        core_new = rewritten.strip()
        if core_orig and not core_new:
            raise SystemExit(
                f"청크 {idx} 윤문 결과({c['rewritten_file']})가 비어 있음 — 유실 사고"
            )
        if not core_orig:
            piece = orig
            ratio = 1.0
        else:
            piece = _leading_ws(orig) + core_new + _trailing_ws(orig)
            ratio = len(core_new) / len(core_orig)
            if ratio < 0.5:
                warnings.append(
                    f"청크 {idx}: 원문 {len(core_orig)}자 → {len(core_new)}자 "
                    f"({ratio:.0%}) — 유실 의심"
                )
            elif ratio > 2.0:
                warnings.append(
                    f"청크 {idx}: 원문 {len(core_orig)}자 → {len(core_new)}자 "
                    f"({ratio:.0%}) — 증식 의심"
                )
        pieces.append(piece)
        report_chunks.append(
            {
                "index": idx,
                "passthrough": False,
                "orig_chars": len(core_orig),
                "rewritten_chars": len(core_new),
                "ratio": round(ratio, 3),
            }
        )

    out = "".join(pieces)
    output_path = run_dir / args.output
    output_path.write_text(out, encoding="utf-8")

    report = {
        "source_chars": len(text),
        "output_chars": len(out),
        "total_ratio": round(len(out) / len(text), 3) if text else None,
        "warnings": warnings,
        "chunks": report_chunks,
    }
    (run_dir / args.report).write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(
        f"output={output_path}\n"
        f"chunks={len(chunks)}\n"
        f"source_chars={len(text)}  output_chars={len(out)}  "
        f"total_ratio={report['total_ratio']}\n"
        f"warnings={len(warnings)}"
    )
    for w in warnings:
        print(f"WARNING: {w}")
    if args.strict and warnings:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
