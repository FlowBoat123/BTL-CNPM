from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from .http_clients import config_meta, run_async_cases, run_sync_case, run_sync_cases, summarize
from .loader import TestSuite, load_suite


def _write_report(path: Path | None, payload: dict[str, Any]) -> None:
    if not path:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def run_suite(suite: TestSuite, mode: str) -> dict[str, Any]:
    if suite.config.warmup:
        warmups = suite.tests[: suite.config.warmup]
        for test in warmups:
            run_sync_case(test, suite.config)

    if mode == "async":
        outcome = asyncio.run(run_async_cases(suite.tests, suite.config))
    elif mode == "sync":
        outcome = run_sync_cases(suite.tests, suite.config)
    else:
        raise ValueError(f"Unsupported mode: {mode}")

    return {
        "meta": {
            "file": str(suite.path),
            "mode": mode,
            "config": config_meta(suite.config),
        },
        **outcome,
    }


def run_many_files(paths: list[Path], base_url: str, mode: str, file_concurrency: int) -> dict[str, Any]:
    started = time.perf_counter()
    suite_results: list[dict[str, Any]] = []

    def worker(path: Path) -> dict[str, Any]:
        return run_suite(load_suite(path, base_url), mode)

    if file_concurrency <= 1:
        for path in paths:
            suite_results.append(worker(path))
    else:
        with ThreadPoolExecutor(max_workers=file_concurrency) as executor:
            futures = [executor.submit(worker, path) for path in paths]
            for future in as_completed(futures):
                suite_results.append(future.result())

    all_results = [item for suite in suite_results for item in suite["results"]]
    wall_time_ms = (time.perf_counter() - started) * 1000
    return {
        "meta": {
            "base_url": base_url,
            "mode": mode,
            "file_concurrency": file_concurrency,
            "files": [str(path) for path in paths],
        },
        "summary": summarize(all_results, wall_time_ms),
        "suites": suite_results,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Advanced pyresttest-compatible YAML runner")
    parser.add_argument("base_url", help="Base URL, for example http://127.0.0.1:5000")
    parser.add_argument("yaml_files", nargs="+", help="One or more pyresttest YAML files")
    parser.add_argument("--mode", choices=["sync", "async"], default="sync", help="HTTP execution mode")
    parser.add_argument("--file-concurrency", type=int, default=1, help="Number of YAML files to run in parallel")
    parser.add_argument("--report", type=Path, default=None, help="Write JSON report to this path")
    parser.add_argument("--fail-fast-exit", action="store_true", help="Return non-zero when any test fails")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    paths = [Path(item) for item in args.yaml_files]
    payload = run_many_files(paths, args.base_url, args.mode, max(1, args.file_concurrency))
    _write_report(args.report, payload)

    summary = payload["summary"]
    print(
        f"{summary['passed']}/{summary['total']} passed, "
        f"failed={summary['failed']}, wall_time_ms={summary['wall_time_ms']:.1f}, "
        f"p95_ms={summary['p95_ms']}"
    )
    if args.report:
        print(f"Report: {args.report}")

    if args.fail_fast_exit and summary["failed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

