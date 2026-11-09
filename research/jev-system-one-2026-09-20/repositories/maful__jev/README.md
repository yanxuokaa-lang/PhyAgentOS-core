# Jevrb

Jevrb is a synchronous Ruby client for the TypeSafe System One API. It returns immutable Ruby objects for every documented answer type.

## Requirements

- Ruby 3.2 or later.
- A TypeSafe API key.

## Installation

Add the gem to your `Gemfile`:

```ruby
gem "jevrb"
```

Install the bundle:

```bash
bundle install
```

## Quick start

Set the API key:

```bash
export TYPESAFE_API_KEY="your-api-key"
```

Create a client and send a request:

```ruby
require "jevrb"

client = Jev::Client.new

result = client.system_one(
  "Help! My payouts have been failing for 3 days.",
  questions: {
    is_urgent: Jev::Noul.build(
      instructions: "Does this convey urgency?"
    ),
    department: Jev::Choice.build(
      instructions: "Which team must handle this?",
      criteria: {
        billing: "Payments, invoicing, and refunds",
        technical: "Bugs, outages, and integrations"
      }
    ),
    frustration: Jev::Score.build(
      instructions: "How frustrated is the customer?",
      criteria: ["Calm", "Frustrated", "Very angry"]
    )
  }
)
```

## Read the result

Each answer is a typed object:

```ruby
result                         # Jev::Result
result.model                   # "jev-1.13.0"
result.usage                   # Jev::Usage
result.answers[:is_urgent]     # Jev::NoulAnswer
result.answers[:department]    # Jev::ChoiceAnswer
result.answers[:frustration]   # Jev::ScoreAnswer
```

Use the grouped accessors when a request contains different question types:

```ruby
result.nouls[:is_urgent].noul

result.choices[:department].choice
result.choices[:department].probabilities
result.choices[:department].confidence

result.scores[:frustration].score
result.scores[:frustration].legend
result.scores[:frustration].probabilities
result.scores[:frustration].confidence
```

## Structured content

The state and instructions accept strings, hashes, and arrays. Nested values must be valid JSON values.

```ruby
question = Jev::Noul.build(
  instructions: {
    potential_duplicate: {
      name: "John Smith",
      location: "Oakland, California"
    },
    question: "Is the resume for the same person as `potential_duplicate`?"
  }
)
```

## Client options

`Jev::Client.new` accepts these options:

| Option | Default |
|---|---|
| `api_key:` | `TYPESAFE_API_KEY` |
| `base_url:` | `TYPESAFE_BASE_URL` or `https://api.typesafe.ai` |
| `model:` | `TYPESAFE_DEFAULT_MODEL` or `jev-latest` |
| `timeout:` | `10.0` seconds |
| `retry_policy:` | `Jev::RetryPolicy.new` |

Set `model:` on `system_one` to replace the client model for one request.

## Retries

The default policy retries connection errors, timeout errors, and these HTTP responses:

- `408 Request Timeout`.
- `429 Too Many Requests`.
- HTTP status codes from 500 through 599.

The policy retries twice after the first request. It obeys `Retry-After` and `retry-after-ms` response headers.

Disable retries when you create the client:

```ruby
client = Jev::Client.new(
  retry_policy: Jev::RetryPolicy.new(max_retries: 0)
)
```

## Errors

All SDK errors inherit from `Jev::Error`.

Client and response errors include these classes:

- `Jev::ConfigurationError`.
- `Jev::ConnectionError`.
- `Jev::TimeoutError`.
- `Jev::ResponseValidationError`.

HTTP errors inherit from `Jev::APIError`. The error exposes `status`, `body`, `headers`, `endpoint`, and `request_id`.

## Static types

The gem includes RBS declarations in `sig/jevrb.rbs`.

Validate the declarations:

```bash
bundle exec rbs -I sig validate
```

## Development

Install the development dependencies:

```bash
bin/setup
```

Run the tests, RBS validation, and RuboCop:

```bash
bundle exec rake
```

## License

Jevrb uses the MIT License.
