# Laravel TypeSafe Jev

[Русская документация](README.ru.md)

Unofficial, community-maintained Laravel integration for [`butochnikov/typesafe-sdk-php`](https://github.com/Butochnikov/typesafe-sdk-php). It is not affiliated with Laravel or TypeSafe.

This package keeps the SDK's typed DTOs, promises, and exceptions while adding Laravel package discovery, scoped lazy DI, configuration, a facade, and a recording fake. Jev `Noul` and `Score` are probability/score questions; this package is not a text-generation or chat client.

## Requirements

| Package | Supported versions |
| --- | --- |
| Laravel 12 | PHP 8.2–8.5 |
| Laravel 13 | PHP 8.3–8.5 |
| TypeSafe SDK | `butochnikov/typesafe-sdk-php:^0.1` |

## Install

```bash
composer require butochnikov/laravel-typesafe-jev
php artisan vendor:publish --tag=jev-config
```

The provider is auto-discovered. Manual registration is also supported with `Butochnikov\LaravelTypeSafeJev\JevServiceProvider::class`. The package does not register a global `Jev` alias.

Set the key in `.env`:

```dotenv
TYPESAFE_API_KEY=your-key
TYPESAFE_DEFAULT_MODEL=jev-latest
TYPESAFE_BASE_URL=https://api.typesafe.ai
TYPESAFE_TIMEOUT=10
```

The key is validated only when a real SDK client is first used, so package discovery, `artisan list`, and `config:cache` work without a key. Config values are the source of truth after caching; the adapter passes these connection settings explicitly to the SDK. Logging has the exception described below. Numeric env values are validated and normalized when the lazy client is resolved. Invalid configuration fails then with a descriptive exception, not during provider registration.

## Use the facade or DI

```php
use Butochnikov\LaravelTypeSafeJev\Facades\Jev;
use TypeSafe\Choice;
use TypeSafe\Noul;
use TypeSafe\Score;

$response = Jev::systemOne(
    state: ['document' => 'Two charges appeared on my card.'],
    questions: [
        'billing' => new Noul(instructions: 'Is this about billing?'),
        'tone' => new Choice(criteria: ['calm' => null, 'angry' => null]),
        'urgency' => new Score(criteria: ['low', 'medium', 'high']),
    ],
);

$tone = $response->choices['tone']->choice;
```

For application services, inject the contract:

```php
use Butochnikov\LaravelTypeSafeJev\Contracts\JevClient;

final class ClassifyDocument
{
    public function __construct(private JevClient $jev) {}
}
```

`systemOne`, `models`, `systemOneAsync`, and `modelsAsync` preserve the SDK response classes. Async methods return `GuzzleHttp\Promise\PromiseInterface` whose value is the corresponding SDK response. `systemOne` also accepts the SDK's per-call `model`, `RetryPolicy`, `Timeout`, `extraHeaders`, and `extraBody` arguments without adding another retry layer.

```php
$promise = Jev::systemOneAsync(['document' => 'test'], [
    'tone' => new Choice(criteria: ['calm' => null, 'angry' => null]),
]);
$response = $promise->wait();
```

For queued jobs, inject the contract into `handle()` rather than serializing a client, promise, or API key:

```php
use Butochnikov\LaravelTypeSafeJev\Contracts\JevClient;
use Illuminate\Contracts\Queue\ShouldQueue;
use TypeSafe\Choice;

final class ClassifyDocumentJob implements ShouldQueue
{
    public function __construct(public readonly string $document) {}

    public function handle(JevClient $jev): void
    {
        $jev->systemOne(['document' => $this->document], [
            'category' => new Choice(criteria: ['billing' => null, 'other' => null]),
        ]);
    }
}
```

The binding is scoped: repeated resolutions in one application scope reuse the lazy adapter, while a new request/job scope receives a new adapter. `close()` is idempotent and cancels pending async work owned by the adapter. Await promises before a request/job ends, or explicitly call `close()` when cancelling work. This package does not require Octane and does not claim that Laravel's generic scope flush automatically calls `close()`.

## Fake and tests

`Jev::fake()` replaces the package contract in the current application scope and never makes network requests. Install it before resolving services that receive `JevClient`. When Laravel clears scoped instances, the original binding is restored; unrelated scoped services are untouched:

```php
use Butochnikov\LaravelTypeSafeJev\Facades\Jev;
use TypeSafe\Choice;
use TypeSafe\ChoiceAnswer;
use TypeSafe\SystemOneResponse;
use TypeSafe\Usage;

$typedResponse = new SystemOneResponse('jev-test', new Usage(), [
    'tone' => new ChoiceAnswer('calm', 0.9, ['calm' => 0.9]),
]);
$fake = Jev::fake([$typedResponse]);
Jev::systemOne(['document' => 'test'], ['tone' => new Choice(['calm' => null])]);
$fake->assertSentCount(1)->assertSent(
    static fn (array $call): bool => $call['operation'] === 'systemOne',
);
```

Use `Jev::fake(models: [$modelsResponse])` for model listing, where `$modelsResponse` is a `TypeSafe\ListModelsResponse`. `calls()` returns recorded arguments; `assertNothingSent()` verifies no calls were made. Install a new fake in each test or scope.

The fake accepts queues of typed `SystemOneResponse`/`ListModelsResponse`, `Throwable` values, or a callback as its third argument. Exhausted or unexpected calls throw immediately. Async fake calls return fulfilled or rejected promises. The SDK clients are final, so the fake is deliberately at the Laravel adapter boundary. Laravel `Http::fake()` does not intercept the SDK's Guzzle client; use `Jev::fake()` or replace `ClientFactory` with a factory using Guzzle's `MockHandler`.

## Configuration and logging

All timeout and backoff values use seconds. `timeout` accepts a positive number or an array such as `['total' => 10, 'connect' => 2, 'read' => 5]`; `total: null` in that array explicitly removes the total timeout.

The published `config/jev.php` contains API key, base URL, model, timeout, headers, retry policy, and logging settings. Retry lists replace the defaults entirely, so `http_statuses: []` disables status retries and `retry.timeout: null` disables the retry budget. Advanced retry predicates or custom HTTP clients belong in an application-provided `ClientFactory`, not in serializable config.

```php
use Butochnikov\LaravelTypeSafeJev\Contracts\ClientFactory;

$this->app->scoped(ClientFactory::class, static fn (): ClientFactory => new MyClientFactory());
```

Logging is disabled by default. When enabled, the configured Laravel channel is passed to the SDK logger; secret headers are redacted by the SDK. SDK 0.1.0 may log response bodies at debug level and independently reads `TYPESAFE_LOG_LEVEL`; this wrapper does not mutate global env or promise that body data is redacted. Do not enable debug logging for sensitive payloads.

The wrapper intentionally does not duplicate HTTP, JSON serialization, response parsing, retry, caching, middleware, or multi-tenant connection systems. See the SDK README for question primitives and wire/API details.

SDK API failures remain SDK exceptions such as `TypeSafe\TypeSafeAPIError`, so applications can catch the original typed error and inspect its status, body, headers, and request ID.

## Development

```bash
composer install
composer check
```

Checks cover Composer metadata, PHP syntax, Pint formatting, PHPUnit/Testbench integration tests, and Larastan at level 8. CI resolves both supported Laravel major versions, including the lowest allowed dependencies. See [RELEASING.md](RELEASING.md) in the source checkout for release steps.

## License

MIT. Copyright (c) 2026 Butochnikov contributors.
