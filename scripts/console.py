"""콘솔 출력 하드닝 — Windows(cp949)에서 게이트가 죽는 것을 막는다. (#84)

## 왜 필요한가

한국어 Windows 콘솔의 기본 인코딩은 `cp949`다. 이 저장소의 스크립트는 stdout에
한글과 em-dash(`—`, U+2014)를 찍는데, cp949는 U+2014를 인코딩하지 못해
**첫 print에서 UnicodeEncodeError로 즉사한다.**

파일 I/O는 전부 `encoding="utf-8"`을 명시하고 있어 데이터 손상은 없다.
순수하게 stdout만의 문제다.

## 더 위험한 부분 — exit code 충돌

파이썬은 처리되지 않은 예외에서 **exit 1**로 끝난다. 그런데 게이트 계약에서
1은 "경고(변경률 30~50%)"다. 즉 **검증이 죽었는데 경고로 읽힌다.**
검증 실패가 정상 판정으로 둔갑하는 것이 이 저장소가 가장 경계하는 실패 형태다
(#59의 "조용히 한 축이 죽는다"와 같은 계열).

`run_gate()`가 예외를 잡아 계약상 "실행 오류"인 **exit 3**으로 보낸다.
"""

from __future__ import annotations

import sys
import traceback
from typing import Callable


def force_utf8_console() -> None:
    """stdout·stderr를 UTF-8로 재설정한다. 실패해도 조용히 통과한다.

    errors="replace" — 재설정이 안 되는 환경에서도 죽지 않고 대체 문자로 넘긴다.
    출력이 조금 깨지는 것이 검증이 통째로 죽는 것보다 낫다.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass  # 파이프·리다이렉트 등 재설정 불가 환경


def run_gate(main: Callable[[], int], *, error_exit_code: int = 3) -> int:
    """게이트 main()을 감싸 콘솔을 하드닝하고 예외를 실행 오류 코드로 보낸다.

    exit 1(경고)과 구분되어야 하므로 기본값은 3(실행 오류)이다.
    """
    force_utf8_console()
    try:
        return main()
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001 — 어떤 예외든 3으로 보내는 것이 목적
        print(f"[gate] 실행 오류 — {type(exc).__name__}: {exc}", file=sys.stderr)
        traceback.print_exc()
        return error_exit_code
