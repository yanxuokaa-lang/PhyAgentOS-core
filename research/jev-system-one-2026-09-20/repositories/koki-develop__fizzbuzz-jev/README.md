# fizzbuzz-jev

[![NPM Version](https://img.shields.io/npm/v/fizzbuzz-jev)](https://www.npmjs.com/package/fizzbuzz-jev)
[![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/koki-develop/fizzbuzz-jev/release-please.yml)](https://github.com/koki-develop/fizzbuzz-jev/actions/workflows/release-please.yml)
[![GitHub License](https://img.shields.io/github/license/koki-develop/fizzbuzz-jev)](./LICENSE)

FizzBuzz powered by [Jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev), TypeSafe AI's System One model.

## Installation

```console
$ npm install fizzbuzz-jev
```

## Usage

Set the `TYPESAFE_API_KEY` environment variable, or pass `apiKey` as the second argument.

```ts
import { fizzbuzz } from "fizzbuzz-jev";

for (let i = 1; i <= 15; i++) {
  const result = await fizzbuzz(i); // Key from TYPESAFE_API_KEY environment variable
  // or
  // const result = await fizzbuzz(i, { apiKey: "YOUR_API_KEY" });

  console.log(result);
}
```

```console
1
2
Fizz
4
Buzz
Fizz
7
8
Fizz
Buzz
11
Fizz
13
14
FizzBuzz
```

### `fizzbuzz(value, config?)`

| Parameter | Type                    | Description                                        |
| --------- | ----------------------- | -------------------------------------------------- |
| `value`   | `number`                | The number to evaluate.                            |
| `config`  | `TypeSafeClientConfig?` | Options passed to `TypeSafeClient` (e.g. `apiKey`). |

Returns `Promise<"Fizz" | "Buzz" | "FizzBuzz" | number>`.

## License

[MIT](./LICENSE)
