# Advanced pyresttest Runner

This package keeps the existing pyresttest YAML style, but adds project-level
features that pyresttest does not provide natively:

- retry with exponential backoff
- sync benchmark/concurrency with `requests`
- async benchmark/concurrency with `aiohttp`
- concurrency control from YAML `config.concurrency`
- `iterations` for repeated test cases
- parallel execution of multiple YAML files
- JSON reports with pass/fail counts and latency percentiles
- quality insights that classify endpoints as stable, slow, flaky, tail-risk, or broken

## Run one file

```powershell
.\.venv\Scripts\python.exe -m tests.pyresttest_ext.runner `
  http://127.0.0.1:5000 `
  tests\pyresttest\concurrent_suite.yaml `
  --mode sync `
  --report tests\reports\advanced_concurrent_report.json `
  --fail-fast-exit
```

## Run async

```powershell
.\.venv\Scripts\python.exe -m tests.pyresttest_ext.runner `
  http://127.0.0.1:5000 `
  tests\pyresttest\concurrent_suite.yaml `
  --mode async `
  --report tests\reports\advanced_concurrent_async_report.json
```

Async mode requires `aiohttp`:

```powershell
.\.venv\Scripts\pip.exe install -r requirements.txt
```

## Run many YAML files in parallel

```powershell
.\.venv\Scripts\python.exe -m tests.pyresttest_ext.runner `
  http://127.0.0.1:5000 `
  tests\pyresttest\smoke.yaml `
  tests\pyresttest\api_suite.yaml `
  --mode sync `
  --file-concurrency 2 `
  --report tests\reports\advanced_all_report.json
```

## Run External Dependencies

External dependencies are isolated in `tests/pyresttest/external_suite.yaml`
because they can be slower or flaky due to network, quota, token, or provider
availability.

```powershell
.\.venv\Scripts\python.exe -m tests.pyresttest_ext.runner `
  http://127.0.0.1:5000 `
  tests\pyresttest\external_suite.yaml `
  --mode sync `
  --report tests\reports\external_report.json
```

This suite checks OpenWeather, Deepseek, and Google OAuth redirect through the
backend. It intentionally does not call SendGrid email sending by default.

## Supported YAML keys

Suite `config`:

- `timeout`
- `concurrency`
- `retry` or `retries`
- `backoff_initial`
- `backoff_factor`
- `backoff_max`
- `warmup`

Test:

- `name`
- `url`
- `method`
- `headers`
- `body`
- `expected_status`
- `validators`
- `iterations`

Benchmark:

- `benchmark_runs` is treated like `iterations`
- `warmup_runs` is used as suite warmup when `config.warmup` is absent

## Generate Test Insights

After running tests, convert JSON reports into an endpoint-level quality view:

```powershell
.\.venv\Scripts\python.exe -m tests.pyresttest_ext.insights `
  tests\reports\advanced_concurrent_sync_report.json `
  tests\reports\advanced_concurrent_async_report.json `
  --md-out tests\reports\test_insights.md `
  --json-out tests\reports\test_insights.json `
  --p95-ms 1000 `
  --retry-rate 0.05
```

The insights report groups results by HTTP method and path, then classifies each
endpoint:

- `stable`: passing and within latency/retry thresholds
- `slow`: p95 latency exceeds the configured threshold
- `tail-risk`: p99 latency exceeds the configured threshold
- `flaky`: retry rate exceeds the configured threshold
- `broken`: failure rate exceeds the configured threshold

## Firebase-Backed Clinic Service Workflow Suite

These tests seed deterministic Firestore documents, run the clinic service workflow suite,
then cleanup the test documents and generated bills.

```powershell
.\.venv\Scripts\python.exe -m tests.pyresttest_ext.clinic_service_workflow run `
  --base-url http://127.0.0.1:5000 `
  --report tests\reports\clinic_service_workflow_report.json
```

The suite uses `tests/pyresttest/clinic_service_workflow_suite.yaml`.

The seeded appointment IDs are:

- `test_e2e_assign_same_doctor`
- `test_e2e_complete_appointment`
- `test-clinic-workflow-session`

The assign-doctor test uses an appointment that is already assigned to the test
doctor so the backend returns `200` without creating a Google Calendar event.
