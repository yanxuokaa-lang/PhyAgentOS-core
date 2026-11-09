# Jev lab

A small Node.js TypeScript CLI for trying TypeSafe's Jev model with synthetic support text.
Run one urgency question, ask 3 questions in one request, or compare their request latencies.
There is no web server or user interface.

## Set up in PowerShell

Install Node.js 20 or newer and Git. Prefer a currently supported Node.js LTS release.
The official SDK requires Node.js 20 or newer.

```powershell
Set-Location C:\Users\mennym\Repos
git clone https://github.com/Menny1337/jev-lab.git
Set-Location .\jev-lab
node --version
npm ci
npm test
npm run typecheck
npm run build
npm start -- --help
```

If you already have the repository, use that checkout instead of cloning it again.
The SDK dependency pins the official upstream v0.6.0 release tarball on GitHub.
The lockfile records its integrity hash. Other dependencies use npm.

## Set your API key without putting it in command history

Get a key from the [TypeSafe dashboard](https://console.typesafe.ai/settings/keys).
These commands prompt for it without echoing it or including it in command history:

```powershell
$secureKey = Read-Host "TypeSafe API key" -AsSecureString
$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
try {
    $env:TYPESAFE_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    Remove-Variable secureKey, pointer
}
```

The key stays in this PowerShell process environment and its child processes.
Remove it when you finish:

```powershell
Remove-Item Env:\TYPESAFE_API_KEY
```

Alternatively, copy the placeholder file and edit `.env` locally:

```powershell
Copy-Item .env.example .env
notepad .env
```

Replace the placeholder in the editor, not in a shell command. Do not share `.env`.
The CLI loads `.env` from the current directory without overriding existing environment values.
An absent, blank or unchanged placeholder key fails before any request.
Help and tests need no key. Never pass a key as a CLI argument.

## Run the examples

```powershell
npm run smoke
npm run batch
npm run benchmark
npm run benchmark -- --warmups 2 --iterations 20 --timeout-ms 30000
```

`smoke` asks an urgency Noul question. `batch` asks urgency, department and frustration
in a single request, not 3 separate calls.

| Question | Type | Interpretation |
| --- | --- | --- |
| urgency | Noul | Probability of urgency from 0 to 1 |
| department | Choice | billing, technical or sales |
| frustration | Score | Expected score on a 0 to 2 rubric, possibly fractional |

Both examples print the JSON response, including the returned model, answers and token usage.
The synthetic text and question definitions are in `src\questions.ts`.
Do not replace them with private customer data without permission.
These examples do not measure accuracy or establish decision thresholds.

All commands request `jev-latest` at `https://api.typesafe.ai/v1/systemone`
through the official `@typesafe-ai/sdk`. The underlying model can change over time.
The CLI fixes the API host, disables SDK logging and automatic retries, and uses
a 30-second timeout unless overridden. It does not use SDK environment overrides
for the host, model or log level.

## Understand the benchmark

The benchmark finishes the one-question case before starting the 3-question case.
Each case runs its warmups first, then its measured attempts. Requests never overlap.
Defaults are one warmup and 5 measured attempts per case: 12 API calls in total.
The total is `2 * (warmups + iterations)`. Calls may incur charges.

| Option | Default | Allowed values |
| --- | --- | --- |
| `--warmups` | 1 | integers from 0 to 1000 |
| `--iterations` | 5 | integers from 1 to 10000 |
| `--timeout-ms` | 30000 | integers from 1 to 300000 |

The console table shows successful measured sample count, median, mean, minimum and
maximum latency in milliseconds. It lists measured and warmup errors separately.
Warmups and failed attempts do not enter latency statistics. An all-failed case has
count 0 and null statistics, not zero latency.

Timing uses a monotonic clock around the awaited SDK call. It includes local SDK work,
network travel, server processing and response parsing. It excludes client construction,
console output and writing results. It is not isolated model inference time.

Every run writes `results\benchmark-<unique-id>.json`. The report includes configuration,
timestamps, the synthetic state, per-attempt latency, phase, response or safe error summary,
and summary statistics. The response records the model actually returned.
Failed calls are printed immediately and retained in the report. The CLI continues the
remaining attempts, writes results and exits with status 1 if any attempt failed,
including a warmup. An interrupted process may leave an empty reserved output file.

Error summaries report HTTP status, timeout or connection failure without dumping
exception bodies or headers. Check your key for HTTP 401, quota for HTTP 429, and
service status for HTTP 5xx. Unexpected local errors prompt you to check file permissions
and service availability. Output redacts exact occurrences of the active API key.

Small samples, case order, connection reuse, server load and network conditions can
affect results. Repeat runs and retain the raw reports before drawing conclusions.
No example output or timing is an accuracy claim, speed guarantee or service-level agreement.

## Develop offline

```powershell
npm test
npm run typecheck
npm run build
node .\dist\cli.js --help
node .\dist\cli.js smoke
```

The last command calls the live API and needs a key. Everything before it works offline
after dependency installation. Tests use mock transports and synthetic responses.
They cover argument and key validation, statistics, warmup exclusion, sequential execution,
failure reporting, SDK request serialization, redaction, help and missing-key errors.
Tests never use a real key or call the API.
GitHub Actions runs these checks on Node.js 20 and 24, on Windows and Ubuntu,
without an API key.

`src\config.ts` owns CLI validation; `src\client.ts` configures the SDK;
`src\benchmark.ts` runs and summarises the benchmark; `src\cli.ts` handles output.
TypeScript checks source and tests in strict mode. Builds emit source only to `dist`.
The project is private in npm to prevent accidental publication.

Git excludes `.env` variants (except `.env.example`), `credentials`, `secrets`,
private-key files, `node_modules`, generated `dist` output and benchmark `results`.
Ignore rules cannot identify every secret: inspect staged changes before pushing
to this public repository.

## Official references

- [TypeSafe quick start](https://docs.typesafe.ai/introduction/quickstart)
- [JavaScript and TypeScript SDK](https://docs.typesafe.ai/sdk/javascript)
- [Official SDK v0.6.0 source and release](https://github.com/typesafe-ai/typesafe-sdk-js/releases/tag/v0.6.0)
