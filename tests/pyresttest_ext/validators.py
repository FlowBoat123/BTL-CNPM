import json
import operator
import re
from typing import Any, Iterable


def jsonpath_mini(data: Any, query: str) -> Any:
    current = data
    for part in str(query).strip(".").split("."):
        if part == "":
            continue
        if isinstance(current, list):
            current = current[int(part)]
        elif isinstance(current, dict):
            current = current[part]
        else:
            return None
    return current


def _body_json(body: str | bytes | None) -> Any:
    if body is None:
        return None
    if isinstance(body, bytes):
        body = body.decode("utf-8", errors="replace")
    return json.loads(body)


def _extract(response: dict[str, Any], config: dict[str, Any]) -> Any:
    if "jsonpath_mini" in config:
        return jsonpath_mini(_body_json(response.get("body")), config["jsonpath_mini"])
    if "raw_body" in config:
        return response.get("body")
    if "header" in config:
        headers = response.get("headers") or {}
        expected = str(config["header"]).lower()
        for key, value in headers.items():
            if key.lower() == expected:
                return value
        return None
    raise ValueError(f"No supported extractor found in validator: {config}")


def _compare(actual: Any, expected: Any, comparator: str) -> bool:
    comparators = {
        "eq": operator.eq,
        "equals": operator.eq,
        "str_eq": lambda a, b: str(a) == str(b),
        "ne": operator.ne,
        "not_equals": operator.ne,
        "lt": operator.lt,
        "less_than": operator.lt,
        "le": operator.le,
        "less_than_or_equal": operator.le,
        "gt": operator.gt,
        "greater_than": operator.gt,
        "ge": operator.ge,
        "greater_than_or_equal": operator.ge,
        "contains": lambda a, b: a is not None and b in a,
        "contained_by": lambda a, b: b is not None and a in b,
        "regex": lambda a, b: re.search(str(b), str(a)) is not None,
        "count_eq": lambda a, b: len(a) == int(b),
        "length_eq": lambda a, b: len(a) == int(b),
    }
    if comparator not in comparators:
        raise ValueError(f"Unsupported comparator: {comparator}")
    return comparators[comparator](actual, expected)


def validate_response(response: dict[str, Any], validators: Iterable[dict[str, Any]] | None) -> list[str]:
    failures: list[str] = []
    for validator in validators or []:
        if "compare" in validator:
            config = validator["compare"] or {}
            comparator = str(config.get("comparator", "eq")).lower()
            expected = config.get("expected")
            try:
                actual = _extract(response, config)
                if not _compare(actual, expected, comparator):
                    failures.append(
                        f"compare failed: comparator={comparator}, actual={actual!r}, expected={expected!r}"
                    )
            except Exception as exc:
                failures.append(f"validator error: {exc}")
        elif "extract_test" in validator:
            config = validator["extract_test"] or {}
            test = str(config.get("test", "exists")).lower()
            try:
                actual = _extract(response, config)
                if test == "exists" and actual is None:
                    failures.append(f"extract_test failed: expected value to exist for {config}")
                elif test in {"not_empty", "notempty"} and not actual:
                    failures.append(f"extract_test failed: expected non-empty value for {config}")
                elif test not in {"exists", "not_empty", "notempty"}:
                    failures.append(f"unsupported extract_test: {test}")
            except Exception as exc:
                failures.append(f"extract_test error: {exc}")
        else:
            failures.append(f"unsupported validator: {validator}")
    return failures
