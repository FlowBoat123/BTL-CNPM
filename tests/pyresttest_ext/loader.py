from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import yaml


@dataclass
class SuiteConfig:
    testset: str = "Default"
    timeout: float = 10.0
    concurrency: int = 1
    retry: int = 0
    backoff_initial: float = 0.25
    backoff_factor: float = 2.0
    backoff_max: float = 5.0
    warmup: int = 0


@dataclass
class TestCase:
    name: str
    method: str
    url: str
    expected_status: list[int]
    headers: dict[str, str] = field(default_factory=dict)
    body: str | None = None
    validators: list[dict[str, Any]] = field(default_factory=list)
    iterations: int = 1
    source: str = ""


@dataclass
class TestSuite:
    path: Path
    config: SuiteConfig
    tests: list[TestCase]


def _as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        merged: dict[str, Any] = {}
        for item in value:
            if isinstance(item, dict):
                merged.update(item)
        return merged
    raise TypeError(f"Expected mapping or list of mappings, got {type(value).__name__}")


def _parse_config(raw: Any) -> SuiteConfig:
    data = _as_dict(raw)
    retry = data.get("retry", data.get("retries", 0))
    return SuiteConfig(
        testset=str(data.get("testset", "Default")),
        timeout=float(data.get("timeout", 10)),
        concurrency=max(1, int(data.get("concurrency", 1))),
        retry=max(0, int(retry or 0)),
        backoff_initial=float(data.get("backoff_initial", data.get("retry_backoff_initial", 0.25))),
        backoff_factor=float(data.get("backoff_factor", data.get("retry_backoff_factor", 2.0))),
        backoff_max=float(data.get("backoff_max", data.get("retry_backoff_max", 5.0))),
        warmup=max(0, int(data.get("warmup", 0))),
    )


def _parse_test(raw: Any, base_url: str, source: str) -> TestCase:
    data = _as_dict(raw)
    expected = data.get("expected_status", [200])
    if not isinstance(expected, list):
        expected = [expected]
    iterations = data.get("iterations", data.get("benchmark_runs", 1))
    return TestCase(
        name=str(data.get("name", data.get("url", "Unnamed"))),
        method=str(data.get("method", "GET")).upper(),
        url=urljoin(base_url.rstrip("/") + "/", str(data["url"]).lstrip("/")),
        expected_status=[int(status) for status in expected],
        headers={str(key): str(value) for key, value in (data.get("headers") or {}).items()},
        body=data.get("body"),
        validators=list(data.get("validators") or []),
        iterations=max(1, int(iterations)),
        source=source,
    )


def load_suite(path: str | Path, base_url: str) -> TestSuite:
    suite_path = Path(path)
    raw = yaml.safe_load(suite_path.read_text(encoding="utf-8")) or []
    config = SuiteConfig()
    tests: list[TestCase] = []

    for node in raw:
        if not isinstance(node, dict):
            continue
        lowered = {str(key).lower(): value for key, value in node.items()}
        if "config" in lowered or "configuration" in lowered:
            config = _parse_config(lowered.get("config", lowered.get("configuration")))
        elif "test" in lowered:
            tests.append(_parse_test(lowered["test"], base_url, str(suite_path)))
        elif "benchmark" in lowered:
            benchmark_config = _as_dict(lowered["benchmark"])
            if "warmup_runs" in benchmark_config and not config.warmup:
                config.warmup = max(0, int(benchmark_config["warmup_runs"]))
            tests.append(_parse_test(benchmark_config, base_url, str(suite_path)))
        elif "url" in lowered:
            tests.append(_parse_test(lowered, base_url, str(suite_path)))
        elif "import" in lowered:
            imported = suite_path.parent / str(lowered["import"])
            imported_suite = load_suite(imported, base_url)
            tests.extend(imported_suite.tests)

    return TestSuite(path=suite_path, config=config, tests=tests)
