from __future__ import annotations

import asyncio
import json
import time
from dataclasses import asdict
from dataclasses import replace
from string import Template
from typing import Any

import requests

from .loader import SuiteConfig, TestCase
from .validators import jsonpath_mini, validate_response


def expand_cases(tests: list[TestCase]) -> list[TestCase]:
    expanded: list[TestCase] = []
    for test in tests:
        expanded.extend([test] * test.iterations)
    return expanded


def _render_value(value: Any, context: dict[str, Any]) -> Any:
    if isinstance(value, dict):
        if set(value.keys()) == {"template"}:
            return Template(str(value["template"])).safe_substitute(context)
        return {key: _render_value(item, context) for key, item in value.items()}
    if isinstance(value, list):
        return [_render_value(item, context) for item in value]
    if isinstance(value, str):
        return Template(value).safe_substitute(context)
    return value


def _render_test(test: TestCase, context: dict[str, Any] | None) -> TestCase:
    if not context:
        return test
    return replace(
        test,
        url=str(_render_value(test.url, context)),
        headers=dict(_render_value(test.headers, context)),
        body=_render_value(test.body, context),
        validators=list(_render_value(test.validators, context)),
    )


def _extract_value(body: str | bytes | None, headers: dict[str, Any], config: dict[str, Any]) -> Any:
    if "jsonpath_mini" in config:
        if body is None:
            return None
        if isinstance(body, bytes):
            body = body.decode("utf-8", errors="replace")
        return jsonpath_mini(json.loads(body), config["jsonpath_mini"])
    if "header" in config:
        expected = str(config["header"]).lower()
        for key, value in headers.items():
            if key.lower() == expected:
                return value
    return None


def _apply_extract_binds(test: TestCase, body: str | bytes | None, headers: dict[str, Any], context: dict[str, Any] | None) -> None:
    if context is None:
        return
    for bind in test.extract_binds:
        for name, config in bind.items():
            context[str(name)] = _extract_value(body, headers, config or {})


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    sorted_values = sorted(values)
    index = min(len(sorted_values) - 1, max(0, int(round((pct / 100.0) * (len(sorted_values) - 1)))))
    return sorted_values[index]


def summarize(results: list[dict[str, Any]], wall_time_ms: float) -> dict[str, Any]:
    elapsed = [item["elapsed_ms"] for item in results if isinstance(item.get("elapsed_ms"), (int, float))]
    failed = [item for item in results if not item.get("ok")]
    return {
        "total": len(results),
        "passed": len(results) - len(failed),
        "failed": len(failed),
        "wall_time_ms": wall_time_ms,
        "p50_ms": percentile(elapsed, 50),
        "p95_ms": percentile(elapsed, 95),
        "p99_ms": percentile(elapsed, 99),
    }


def _backoff_delay(config: SuiteConfig, attempt_index: int) -> float:
    delay = config.backoff_initial * (config.backoff_factor ** attempt_index)
    return min(config.backoff_max, delay)


def _result_from_response(test: TestCase, status_code: int | None, body: str | bytes | None, headers: dict[str, Any], elapsed_ms: float, error: str | None, attempt: int) -> dict[str, Any]:
    response = {"body": body, "headers": headers}
    failures = []
    if status_code not in test.expected_status:
        failures.append(f"status {status_code} not in expected {test.expected_status}")
    if not failures:
        failures.extend(validate_response(response, test.validators))
    return {
        "name": test.name,
        "source": test.source,
        "method": test.method,
        "url": test.url,
        "expected_status": test.expected_status,
        "status_code": status_code,
        "ok": not failures and error is None,
        "elapsed_ms": elapsed_ms,
        "attempts": attempt,
        "error": error,
        "failures": failures,
        "response_snippet": body[:500] if isinstance(body, str) and failures else None,
    }


def run_sync_case(
    test: TestCase,
    config: SuiteConfig,
    session: requests.Session | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    requester = session or requests.Session()
    last_result: dict[str, Any] | None = None
    rendered_test = _render_test(test, context)
    for attempt in range(1, config.retry + 2):
        started = time.perf_counter()
        try:
            response = requester.request(
                rendered_test.method,
                rendered_test.url,
                data=rendered_test.body,
                headers=rendered_test.headers,
                timeout=config.timeout,
                allow_redirects=rendered_test.follow_redirects,
            )
            elapsed_ms = (time.perf_counter() - started) * 1000
            last_result = _result_from_response(
                rendered_test,
                response.status_code,
                response.text,
                dict(response.headers),
                elapsed_ms,
                None,
                attempt,
            )
        except requests.RequestException as exc:
            elapsed_ms = (time.perf_counter() - started) * 1000
            last_result = _result_from_response(rendered_test, None, None, {}, elapsed_ms, str(exc), attempt)

        if last_result["ok"] or attempt > config.retry:
            if last_result["ok"]:
                _apply_extract_binds(rendered_test, response.text, dict(response.headers), context)
            return last_result
        time.sleep(_backoff_delay(config, attempt - 1))

    return last_result or _result_from_response(rendered_test, None, None, {}, 0, "unknown error", 0)


def run_sync_cases(tests: list[TestCase], config: SuiteConfig) -> dict[str, Any]:
    from concurrent.futures import ThreadPoolExecutor, as_completed

    expanded = expand_cases(tests)
    started = time.perf_counter()
    results: list[dict[str, Any]] = []
    context = dict(config.variable_binds)
    if config.concurrency <= 1:
        with requests.Session() as session:
            for test in expanded:
                results.append(run_sync_case(test, config, session=session, context=context))
        wall_time_ms = (time.perf_counter() - started) * 1000
        return {"summary": summarize(results, wall_time_ms), "results": results}
    with ThreadPoolExecutor(max_workers=config.concurrency) as executor:
        futures = [executor.submit(run_sync_case, test, config, None, context) for test in expanded]
        for future in as_completed(futures):
            results.append(future.result())
    wall_time_ms = (time.perf_counter() - started) * 1000
    return {"summary": summarize(results, wall_time_ms), "results": results}


async def run_async_case(test: TestCase, config: SuiteConfig, session: Any, semaphore: asyncio.Semaphore) -> dict[str, Any]:
    last_result: dict[str, Any] | None = None
    async with semaphore:
        rendered_test = _render_test(test, config.variable_binds)
        for attempt in range(1, config.retry + 2):
            started = time.perf_counter()
            try:
                async with session.request(
                    rendered_test.method,
                    rendered_test.url,
                    data=rendered_test.body,
                    headers=rendered_test.headers,
                    timeout=config.timeout,
                    allow_redirects=rendered_test.follow_redirects,
                ) as response:
                    body = await response.text()
                    elapsed_ms = (time.perf_counter() - started) * 1000
                    last_result = _result_from_response(
                        rendered_test,
                        response.status,
                        body,
                        dict(response.headers),
                        elapsed_ms,
                        None,
                        attempt,
                    )
            except Exception as exc:
                elapsed_ms = (time.perf_counter() - started) * 1000
                last_result = _result_from_response(rendered_test, None, None, {}, elapsed_ms, str(exc), attempt)

            if last_result["ok"] or attempt > config.retry:
                return last_result
            await asyncio.sleep(_backoff_delay(config, attempt - 1))

    return last_result or _result_from_response(rendered_test, None, None, {}, 0, "unknown error", 0)


async def run_async_cases(tests: list[TestCase], config: SuiteConfig) -> dict[str, Any]:
    try:
        import aiohttp
    except ImportError as exc:
        raise RuntimeError("Async mode requires aiohttp. Install dependencies with: pip install -r requirements.txt") from exc

    expanded = expand_cases(tests)
    semaphore = asyncio.Semaphore(config.concurrency)
    started = time.perf_counter()
    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(*(run_async_case(test, config, session, semaphore) for test in expanded))
    wall_time_ms = (time.perf_counter() - started) * 1000
    return {"summary": summarize(list(results), wall_time_ms), "results": list(results)}


def config_meta(config: SuiteConfig) -> dict[str, Any]:
    return asdict(config)
