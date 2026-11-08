"""Phase 31 - capture one Basys-3 trial over UART and score it.

Usage (Windows, board on e.g. COM5):
    python capture_and_score.py --port COM5 --variant clean
    python capture_and_score.py --port COM5 --variant t01_one_sided
    ...
Then, once all five are captured:
    python capture_and_score.py --report

Captures land in evidence/<variant>/trial<N>.bin. Press the board's reset
(btnC) to re-run the suite; the script waits for a fresh NTD1 sync each time.

Requires pyserial:  pip install pyserial
"""

import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVIDENCE = HERE / "evidence"

SYNC = b"NTD1"
RECORD_BYTES = 23
PACKETS = 13
TOTAL = RECORD_BYTES * PACKETS  # 299

VARIANTS = [
    "clean",
    "t01_self_consistent",
    "t01_one_sided",
    "t0512_self_consistent",
    "t0512_one_sided",
]


def crc8(data) -> int:
    """CRC-8/ATM, polynomial 0x07, init 0 - same as decode_uart.py."""
    value = 0
    for byte in data:
        value ^= byte
        for _ in range(8):
            value = ((value << 1) ^ 0x07) & 0xFF if value & 0x80 else (value << 1) & 0xFF
    return value


def capture(port: str, baud: int, variant: str, trial: int, timeout: float) -> Path:
    import serial  # pyserial

    out_dir = EVIDENCE / variant
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"trial{trial}.bin"

    print(f"[{variant}] listening on {port} at {baud} - press btnC to run the suite")
    with serial.Serial(port, baud, timeout=timeout) as handle:
        buffer = bytearray()
        while True:
            chunk = handle.read(max(1, handle.in_waiting))
            if not chunk:
                raise SystemExit("timed out waiting for data - is the board programmed?")
            buffer += chunk
            start = buffer.find(SYNC)
            if start >= 0 and len(buffer) - start >= TOTAL:
                record = bytes(buffer[start : start + TOTAL])
                break
    path.write_bytes(record)
    print(f"[{variant}] captured {len(record)} bytes -> {path}")
    return path


def decode(record: bytes):
    rows = []
    for index in range(PACKETS):
        raw = record[index * RECORD_BYTES : (index + 1) * RECORD_BYTES]
        body, checksum = raw[:-1], raw[-1]
        trace_length = raw[10] & 0x0F
        trace = list(raw[11:11 + min(trace_length, 8)])
        rows.append(
            {
                "packet": raw[4],
                "physical_source": raw[8],
                "delivered_physical": None,
                "delivered_logical": None if raw[9] == 0xFF else (raw[9] & 0x0F),
                "trace_length": trace_length,
                "trace": trace,
                "observation_cycles": raw[21],
                "crc_ok": crc8(body) == checksum,
                "sync_ok": raw[:4] == SYNC,
            }
        )
    return rows


def report() -> None:
    captures = {}
    for variant in VARIANTS:
        files = sorted((EVIDENCE / variant).glob("trial*.bin")) if (EVIDENCE / variant).exists() else []
        if files:
            captures[variant] = [path.read_bytes() for path in files]

    if "clean" not in captures:
        raise SystemExit("no clean capture found - capture the clean variant first")

    clean = captures["clean"][0]
    clean_rows = decode(clean)

    print()
    print(f"{'variant':>24} {'trials':>7} {'stable':>7} {'route':>10} {'endpoint':>10} {'verdict':>14}")
    print("-" * 78)
    results = {}
    for variant in VARIANTS:
        if variant not in captures:
            print(f"{variant:>24} {'--':>7} {'--':>7} {'--':>10} {'--':>10} {'NOT CAPTURED':>14}")
            continue
        trials = captures[variant]
        stable = all(t == trials[0] for t in trials)
        rows = decode(trials[0])
        route_diff = sum(
            1 for a, b in zip(rows, clean_rows) if a["trace"] != b["trace"]
        )
        endpoint_diff = sum(
            1 for a, b in zip(rows, clean_rows)
            if a["delivered_logical"] != b["delivered_logical"]
        )
        if variant == "clean":
            verdict = "KNOWN(clean)"
        elif route_diff and not endpoint_diff:
            verdict = "self-consistent"
        elif endpoint_diff and not route_diff:
            verdict = "one-sided"
        elif not route_diff and not endpoint_diff:
            verdict = "IDENTICAL(!)"
        else:
            verdict = "BOTH(!)"
        results[variant] = dict(
            stable=stable, route_diff=route_diff, endpoint_diff=endpoint_diff,
            verdict=verdict, trials=len(trials),
            sha256=hashlib.sha256(trials[0]).hexdigest(),
        )
        print(f"{variant:>24} {len(trials):>7} {str(stable):>7} "
              f"{route_diff:>4}/{PACKETS:<5} {endpoint_diff:>4}/{PACKETS:<5} {verdict:>14}")

    print()
    print("Expected, if the duality in Table II holds on silicon:")
    print("  *_self_consistent : route differs, endpoint matches clean")
    print("  *_one_sided       : route byte-identical to clean, endpoint differs")
    print()
    bad = [v for v, r in results.items()
           if v != "clean" and r["verdict"] in ("IDENTICAL(!)", "BOTH(!)")]
    if bad:
        print(f"!! {', '.join(bad)} contradict the duality claim. Do not submit without")
        print("   re-checking Table II and Fig. 2 against this.")
    else:
        crc_bad = sum(1 for v in captures for r in decode(captures[v][0]) if not r["crc_ok"])
        print(f"All variants consistent with the claim. CRC failures across captures: {crc_bad}")

    (EVIDENCE / "summary.json").write_text(json.dumps(results, indent=2))
    print(f"\nwrote {EVIDENCE / 'summary.json'}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--variant", choices=VARIANTS)
    parser.add_argument("--trial", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args()

    if args.report:
        report()
        return
    if not args.port or not args.variant:
        raise SystemExit("need --port and --variant, or --report")
    capture(args.port, args.baud, args.variant, args.trial, args.timeout)


if __name__ == "__main__":
    main()
