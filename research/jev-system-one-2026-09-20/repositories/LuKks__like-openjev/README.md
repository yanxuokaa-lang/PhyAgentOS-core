# like-openjev

Official JavaScript library for the OpenJEV API

```sh
npm i like-openjev
```

https://openjev.sh

## Usage

```js
import OpenJev from 'like-openjev'

const jev = new OpenJev({
  apiKey: process.env.OPENJEV_API_KEY
})

const response = await jev.ask('My card was charged twice. Please help ASAP.', {
  urgent: {
    type: 'noul',
    instructions: 'Does this message convey urgency?',
    criteria: {
      true: 'Explicitly time-sensitive',
      false: 'No urgency expressed'
    }
  },
  team: {
    type: 'choice',
    instructions: 'Which team should handle this?',
    criteria: {
      billing: 'Payments and refunds',
      technical: 'Bugs and integrations',
      sales: 'Pricing and new accounts'
    }
  }
})

console.log(response.answers.urgent.noul) // => 0.98
console.log(response.answers.team.choice) // => 'billing'
```

## API

#### `jev = new OpenJev(options = {})`

Create a client.

```js
{
  apiKey: process.env.OPENJEV_API_KEY, // This is the default and can be omitted
  baseUrl: 'https://api.openjev.sh'
}
```

#### `response = await jev.ask(state, questions)`

Send one state and any number of questions.

- `state`: a string, object, or array.
- `questions`: a map of question ids to `noul`, `choice`, or `score` questions.

```js
const response = await jev.ask('My card was charged twice. Please help ASAP.', {
  team: {
    type: 'choice',
    instructions: 'Which team should handle this?',
    criteria: {
      billing: 'Payments and refunds',
      technical: 'Bugs and integrations',
      sales: 'Pricing and new accounts'
    }
  }
})

console.log(response.answers) /* => {
  team: {
    type: 'choice',
    choice: 'billing',
    probabilities: { sales: 0, technical: 0, billing: 1 },
    confidence: 1
  }
} */
```

#### `response = await jev.bool(state, instructions, criteria)`

Send one `noul` question. The result is returned under `response.answers.answer.noul`.

```js
const response = await jev.bool(
  'My card was charged twice. Please help ASAP.',
  'Does this message convey urgency?',
  {
    true: 'Explicitly time-sensitive',
    false: 'No urgency expressed'
  }
)

console.log(response.answers.answer) /* => {
  type: 'noul',
  noul: 0.98
} */
```

#### `response = await jev.choice(state, instructions, criteria)`

Send one `choice` question. The result is returned under `response.answers.answer.choice`.

```js
const response = await jev.choice(
  'My card was charged twice. Please help ASAP.',
  'Which team should handle this?',
  {
    billing: 'Payments and refunds',
    technical: 'Bugs and integrations',
    sales: 'Pricing and new accounts'
  }
)

console.log(response.answers.answer) /* {
  type: 'choice',
  choice: 'billing',
  probabilities: { technical: 0, sales: 0, billing: 1 },
  confidence: 1
} */
```

#### `response = await jev.score(state, instructions, criteria)`

Send one `score` question. The result is returned under `response.answers.answer.score`.

```js
const response = await jev.score(
  'My card was charged twice. Please help ASAP.',
  'How frustrated is this customer?',
  ['Calm', 'Frustrated', 'Very angry']
)

console.log(response.answers.answer) /* => {
  type: 'score',
  score: 1.02,
  legend: { '0': 'Calm', '1': 'Frustrated', '2': 'Very angry' },
  probabilities: { '0': 0, '1': 0.98, '2': 0.02 },
  confidence: 0.97
} */
```

#### `response = await jev.request(pathname, body)`

Send a raw request.

```js
const response = await jev.request('/v1/systemone', { ... })
```

See advanced docs: https://openjev.sh/docs/advanced

## Errors

```js
try {
  await jev.ask('My card was charged twice.', {})
} catch (err) {
  console.error(err.code, err.message)
}
```

Error codes:

- `API_CONNECTION_ERROR`: the API could not be reached.
- `BAD_REQUEST_ERROR`: HTTP 400.
- `AUTHENTICATION_ERROR`: HTTP 401 or a missing API key.
- `UNPROCESSABLE_ENTITY_ERROR`: HTTP 422.
- `SERVICE_UNAVAILABLE_ERROR`: HTTP 503.

## License

MIT
