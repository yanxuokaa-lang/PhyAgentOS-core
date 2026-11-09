# Connector for TypeSafe Jev

[![CI](https://github.com/juanlentino/jev-connector/actions/workflows/ci.yml/badge.svg)](https://github.com/juanlentino/jev-connector/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/juanlentino/jev-connector?label=release)](https://github.com/juanlentino/jev-connector/releases/latest)
[![WordPress 7.0+](https://img.shields.io/badge/WordPress-7.0%2B-21759b)](https://wordpress.org/download/)
[![PHP 7.4+](https://img.shields.io/badge/PHP-7.4%2B-777bb4)](https://www.php.net/supported-versions.php)
[![License: GPL-2.0-or-later](https://img.shields.io/badge/license-GPL--2.0--or--later-blue)](LICENSE)

A WordPress connector for the [TypeSafe](https://docs.typesafe.ai) System One API. It gives your themes and plugins a typed way to ask questions about content and get back values you can branch on: a probability, a named choice, or a score, each with a confidence figure.

No prose parsing. No prompt wrangling in your template files.

**Status:** 0.x, pending review for the WordPress plugin directory. The public API may still move before 1.0; changes are recorded in [CHANGELOG.md](CHANGELOG.md).

## Requirements

- WordPress 7.0 or later (the key is managed by core's Connectors API; there is no fallback field)
- PHP 7.4 or later
- A TypeSafe API key from the [console](https://console.typesafe.ai/keys)

## Why typed answers

Jev answers three kinds of question, and many of them in a single call:

| Primitive | Question | Answer |
| --- | --- | --- |
| `noul` | "Is this comment spam?" | `0.94` |
| `choice` | "Which category fits?" | `"essays"` plus a distribution and confidence |
| `score` | "How severe is this?" | `1.3` on a scale you defined, plus confidence |

## Install

**From a release zip**

Download the latest zip from [Releases](https://github.com/juanlentino/jev-connector/releases) and install it through **Plugins → Add New → Upload Plugin**.

**From source**

```bash
git clone https://github.com/juanlentino/jev-connector.git wp-content/plugins/connector-for-typesafe-jev
```

## Configure

Requires WordPress 7.0, because the key is managed by the core [Connectors API](https://make.wordpress.org/core/2026/03/18/introducing-the-connectors-api-in-wordpress-7-0/) rather than by anything this plugin invented.

Go to **Settings → Connectors**, find the TypeSafe Jev card, and paste a key from the [TypeSafe console](https://console.typesafe.ai/keys). Core stores it, masks it in the UI and in REST responses, and resolves it in this order:

1. `TYPESAFE_API_KEY` environment variable
2. `TYPESAFE_API_KEY` constant in `wp-config.php`
3. The stored option

Nothing is sent to TypeSafe until a key resolves, and then only when your own code makes a call.

### No screens of its own

Like the Anthropic and Google provider connectors, this plugin adds no menu. The card is the whole UI. The default model and the REST capability are code-level choices:

```php
add_filter( 'jevc_default_model', fn() => 'jev-1.13' );
add_filter( 'jevc_rest_capability', fn() => 'manage_options' );
```

What a site does with an answer (moderate a comment, tag a post, grade a draft) belongs to the plugin or theme that owns that content. [Signal & Noise Tools](https://github.com/juanlentino/signal-and-noise-tools) is the first consumer built that way.

### Not an AI provider, on purpose

The core AI Client is generative: text, image, speech, video. Jev is not. It returns a probability, a choice, or a score with a confidence figure, and routing that through `generate_text()` throws away everything worth having. Core also special-cases `type => 'ai_provider'` by validating those keys against the AI Client and clearing the ones it cannot verify, which would quietly wipe a working Jev key.

So this registers as a non-generative service connector, the way a spam filter does. You still get core's key management. You just don't get misfiled.

## Use

```php
use JevConnector\Question;

$answer = JevConnector\ask(
    array(
        'title' => get_the_title(),
        'body'  => wp_strip_all_tags( get_the_content() ),
    ),
    array(
        'is_technical' => Question::noul( 'Does this post assume programming knowledge?' ),
        'audience'     => Question::choice(
            'Who is this written for?',
            array(
                'practitioner' => 'People who will act on it this week',
                'executive'    => 'People who fund the work but will not do it',
                'general'      => 'Interested readers with no stake',
            )
        ),
        'evidence'     => Question::score(
            'How well is the central claim supported?',
            array(
                'Assertion with no support',
                'Anecdote or a single example',
                'Cited sources a reader can check',
            )
        ),
    )
);

if ( is_wp_error( $answer ) ) {
    error_log( $answer->get_error_message() );
    return;
}

$answer->noul( 'is_technical' );          // 0.91
$answer->choice( 'audience' );            // 'practitioner'
$answer->confidence( 'audience' );        // 0.74
$answer->probabilities( 'audience' );     // [ 'practitioner' => 0.74, ... ]
$answer->score( 'evidence' );             // 1.6
$answer->is_confident( 'audience', 0.9 ); // false — do not act automatically
$answer->usage();                         // [ 'input_tokens' => 412, ... ]
```

### Confidence gating

Gate on consequences, not on a single global threshold. Reads and suggestions can run at 0.5; anything that deletes, publishes, or emails should want 0.9 or a human.

```php
if ( $answer->is_confident( 'route', 0.9 ) ) {
    act( $answer->choice( 'route' ) );
} elseif ( $answer->is_confident( 'route', 0.6 ) ) {
    flag_for_review();
} else {
    leave_it_alone();
}
```

For a `noul`, `is_confident()` measures distance from 0.5, so 0.97 and 0.03 are both confident and 0.52 is not.

## REST

Full reference, with every error code, in [docs/REST-API.md](docs/REST-API.md).

`POST /wp-json/jev/v1/ask` — same payload shape as the PHP helper. Requires a logged-in user with `edit_posts` by default (`jevc_rest_capability` filter).

```js
await apiFetch( {
    path: '/jev/v1/ask',
    method: 'POST',
    data: {
        state: { body: content },
        questions: {
            headline: { type: 'noul', instructions: 'Does the headline match the body?' },
        },
    },
} );
```

`GET /wp-json/jev/v1/status` reports whether the connector is ready.

## Hooks

Full signatures and firing order are in [docs/HOOKS.md](docs/HOOKS.md).

| Hook | Type | Purpose |
| --- | --- | --- |
| `jevc_default_model` | filter | The model id when a call passes none (default `jev-latest`) |
| `jevc_http_timeout` | filter | Request timeout in seconds (default 20) |
| `jevc_request_payload` | filter | Last look at the body before encoding |
| `jevc_request_args` | filter | Arguments handed to `wp_remote_post()` |
| `jevc_retry_delay` | filter | Backoff in seconds; return 0 to disable sleeping |
| `jevc_rest_capability` | filter | Capability required by the REST route |
| `jevc_cache_ttl` | filter | Response cache lifetime; return 0 to disable |
| `jevc_connector_type` | filter | Connector type used to group the card |
| `jevc_connector_args` | filter | The whole connector definition before registration |
| `jevc_after_response` | action | Fires with the `Response` on success |
| `jevc_request_failed` | action | Fires with the `WP_Error` on final failure |

## Caching

Identical requests are served from a transient keyed by a hash of the exact payload, so re-evaluating the same draft or comment costs nothing. Any change to the state, the questions, or the model is a miss. Failures are never cached.

```php
add_filter( 'jevc_cache_ttl', fn() => 0 );              // disable globally
JevConnector\ask( $state, $questions, [ 'cache' => false ] ); // bypass once
```

## Errors

Everything returns `WP_Error` rather than throwing. Codes: `jevc_not_configured`, `jevc_invalid_question`, `jevc_invalid_response`, `jevc_encode_failed`, and `jevc_http_<status>`. 429, 529 and 5xx are retried three times with backoff before giving up.

## Development

```bash
composer install
composer check  # lint + tests
```

- [CONTRIBUTING.md](CONTRIBUTING.md): setup, what CI runs, how to make a change
- [CLAUDE.md](CLAUDE.md): the design decisions that must not be quietly reversed, with reasons
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): file map and the request path end to end
- [docs/RELEASING.md](docs/RELEASING.md): version bump, tag, zip, and the directory's SVN
- [SECURITY.md](SECURITY.md): what is sent where, and how to report a vulnerability
- [SUBMITTING.md](SUBMITTING.md): the pre-submission checklist for the plugin directory

`trunk` is protected. Every change goes through a pull request with PHPUnit on PHP 7.4 to 8.5, WordPress Coding Standards, and the directory's own Plugin Check all green.

## License

GPL-2.0-or-later. TypeSafe and Jev are trademarks of their owner; this plugin is an independent client and is not affiliated with or endorsed by TypeSafe. The TypeSafe mark in `assets/images/` is used only to identify the service on the core Connectors card, the way every connector card identifies its service, and will be removed on request.
