from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


@dataclass
class InsightThresholds:
    p95_ms: float = 1000.0
    p99_ms: float = 2000.0
    retry_rate: float = 0.05
    failure_rate: float = 0.0


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((pct / 100.0) * (len(ordered) - 1)))))
    return ordered[index]


def _iter_results(report: dict[str, Any]) -> list[dict[str, Any]]:
    if "results" in report:
        return list(report["results"])
    results: list[dict[str, Any]] = []
    for suite in report.get("suites", []):
        results.extend(suite.get("results", []))
    return results


def _endpoint_key(result: dict[str, Any]) -> str:
    url = str(result.get("url", ""))
    parsed = urlparse(url)
    path = parsed.path or url
    return f"{result.get('method', 'GET')} {path}"


def _classify(stats: dict[str, Any], thresholds: InsightThresholds) -> str:
    if stats["failure_rate"] > thresholds.failure_rate:
        return "broken"
    if stats["retry_rate"] > thresholds.retry_rate:
        return "flaky"
    if stats["p95_ms"] is not None and stats["p95_ms"] > thresholds.p95_ms:
        return "slow"
    if stats["p99_ms"] is not None and stats["p99_ms"] > thresholds.p99_ms:
        return "tail-risk"
    return "stable"


def analyze_reports(report_paths: list[Path], thresholds: InsightThresholds) -> dict[str, Any]:
    all_results: list[dict[str, Any]] = []
    for path in report_paths:
        with path.open(encoding="utf-8") as handle:
            report = json.load(handle)
        for result in _iter_results(report):
            result = dict(result)
            result["_report"] = str(path)
            all_results.append(result)

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in all_results:
        groups[_endpoint_key(result)].append(result)

    endpoint_stats: list[dict[str, Any]] = []
    for endpoint, results in groups.items():
        total = len(results)
        failed = sum(1 for item in results if not item.get("ok"))
        retried = sum(1 for item in results if int(item.get("attempts") or 1) > 1)
        latencies = [float(item["elapsed_ms"]) for item in results if isinstance(item.get("elapsed_ms"), (int, float))]
        stats = {
            "endpoint": endpoint,
            "total": total,
            "passed": total - failed,
            "failed": failed,
            "failure_rate": failed / total if total else 0,
            "retried": retried,
            "retry_rate": retried / total if total else 0,
            "p50_ms": percentile(latencies, 50),
            "p95_ms": percentile(latencies, 95),
            "p99_ms": percentile(latencies, 99),
            "max_ms": max(latencies) if latencies else None,
        }
        stats["classification"] = _classify(stats, thresholds)
        endpoint_stats.append(stats)

    endpoint_stats.sort(
        key=lambda item: (
            item["classification"] == "stable",
            -(item["failure_rate"] or 0),
            -(item["retry_rate"] or 0),
            -(item["p95_ms"] or 0),
        )
    )

    total = len(all_results)
    failed = sum(1 for item in all_results if not item.get("ok"))
    retried = sum(1 for item in all_results if int(item.get("attempts") or 1) > 1)
    classifications = defaultdict(int)
    for item in endpoint_stats:
        classifications[item["classification"]] += 1

    return {
        "meta": {
            "reports": [str(path) for path in report_paths],
            "thresholds": thresholds.__dict__,
        },
        "summary": {
            "total": total,
            "passed": total - failed,
            "failed": failed,
            "failure_rate": failed / total if total else 0,
            "retried": retried,
            "retry_rate": retried / total if total else 0,
            "endpoint_count": len(endpoint_stats),
            "classifications": dict(sorted(classifications.items())),
        },
        "endpoints": endpoint_stats,
    }


def render_markdown(analysis: dict[str, Any]) -> str:
    summary = analysis["summary"]
    lines = [
        "# Test Insights",
        "",
        "## Summary",
        "",
        f"- Total requests: {summary['total']}",
        f"- Passed: {summary['passed']}",
        f"- Failed: {summary['failed']}",
        f"- Retry recovered/attempted requests: {summary['retried']}",
        f"- Retry rate: {summary['retry_rate']:.2%}",
        f"- Endpoint count: {summary['endpoint_count']}",
        f"- Classifications: {summary['classifications']}",
        "",
        "## Endpoint Health",
        "",
        "| Classification | Endpoint | Passed/Total | Retry Rate | p95 ms | p99 ms | Max ms |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for item in analysis["endpoints"]:
        lines.append(
            "| {classification} | `{endpoint}` | {passed}/{total} | {retry_rate:.2%} | {p95} | {p99} | {max_ms} |".format(
                classification=item["classification"],
                endpoint=item["endpoint"],
                passed=item["passed"],
                total=item["total"],
                retry_rate=item["retry_rate"],
                p95=_fmt_number(item["p95_ms"]),
                p99=_fmt_number(item["p99_ms"]),
                max_ms=_fmt_number(item["max_ms"]),
            )
        )
    return "\n".join(lines) + "\n"


def _fmt_number(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.1f}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze advanced pyresttest JSON reports")
    parser.add_argument("reports", nargs="+", type=Path, help="JSON report files from tests.pyresttest_ext.runner")
    parser.add_argument("--json-out", type=Path, default=None, help="Write machine-readable insights JSON")
    parser.add_argument("--md-out", type=Path, default=None, help="Write Markdown insights report")
    parser.add_argument("--p95-ms", type=float, default=1000.0, help="Endpoint p95 threshold for slow classification")
    parser.add_argument("--p99-ms", type=float, default=2000.0, help="Endpoint p99 threshold for tail-risk classification")
    parser.add_argument("--retry-rate", type=float, default=0.05, help="Retry-rate threshold for flaky classification")
    parser.add_argument("--failure-rate", type=float, default=0.0, help="Failure-rate threshold for broken classification")
    parser.add_argument("--fail-on-risk", action="store_true", help="Return non-zero if any endpoint is not stable")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    thresholds = InsightThresholds(
        p95_ms=args.p95_ms,
        p99_ms=args.p99_ms,
        retry_rate=args.retry_rate,
        failure_rate=args.failure_rate,
    )
    analysis = analyze_reports(args.reports, thresholds)

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(analysis, indent=2, ensure_ascii=False), encoding="utf-8")
    if args.md_out:
        args.md_out.parent.mkdir(parents=True, exist_ok=True)
        args.md_out.write_text(render_markdown(analysis), encoding="utf-8")

    summary = analysis["summary"]
    print(
        f"insights: endpoints={summary['endpoint_count']}, "
        f"failed={summary['failed']}, retry_rate={summary['retry_rate']:.2%}, "
        f"classifications={summary['classifications']}"
    )

    if args.fail_on_risk:
        risky = [item for item in analysis["endpoints"] if item["classification"] != "stable"]
        return 1 if risky else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
