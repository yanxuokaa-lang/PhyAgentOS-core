# verdict — Eio client for TypeSafe AI's Jev model

`verdict` is an OCaml 5.2+ client SDK for the
[TypeSafe AI](https://api.typesafe.ai) system-one evaluation API. Questions and
answers are typed: a question handle carries its answer type, so an answer
cannot be read as the wrong kind of answer. Bounded requests, TLS and retries
are handled for you.

This is an independent client library, not an official TypeSafe product.

## Installation

Requires OCaml 5.2 or newer. From a checkout of this repository:

```sh
opam pin add verdict .
```

## Usage

`Config.create` picks up the API key from `TYPESAFE_API_KEY`:

```ocaml
let ( let* ) = Result.bind

let evaluate ~sw ~net ~clock =
  let open Verdict in
  let* config = Config.create ~timeout:10. () in
  let* client = Client.create ~net ~clock config in
  let* spam =
    Question.noul
      ~id:"spam"
      ~instructions:(Content.text "Is this message unsolicited advertising?")
      ()
  in
  let* tone =
    Question.choice
      ~id:"tone"
      ~instructions:(Content.text "What is the tone of this message?")
      [ "angry", Some (Content.text "Upset or hostile")
      ; "calm", Some (Content.text "Neutral or polite")
      ; "excited", None
      ]
      ()
  in
  let* request =
    Request.create
      ~state:(Content.text "I was charged twice for the same subscription. Please help.")
      [ Question.pack spam; Question.pack tone ]
  in
  let* response = Client.evaluate client ~sw request in
  (match Response.find response spam with
   | Some answer ->
     Printf.printf "spam probability = %.3f\n" (Probability.to_float answer.probability)
   | None -> print_endline "spam: no answer");
  (match Response.find response tone with
   | Some answer ->
     Printf.printf
       "tone = %s (confidence %.3f)\n"
       answer.choice
       (Confidence.to_float answer.confidence)
   | None -> print_endline "tone: no answer");
  Ok ()
;;

let () =
  Eio_main.run (fun env ->
    Eio.Switch.run (fun sw ->
      match evaluate ~sw ~net:(Eio.Stdenv.net env) ~clock:(Eio.Stdenv.clock env) with
      | Ok () -> ()
      | Error e ->
        prerr_endline (Verdict.Error.message e);
        exit 1))
;;
```

`Response` also exposes the model that answered, token usage, the server's
request id, and the raw JSON. Runnable versions of this and `list_models` live
in [`examples/`](examples).

## Configuration

`Config.create` reads `TYPESAFE_API_KEY`, `TYPESAFE_BASE_URL` and
`TYPESAFE_DEFAULT_MODEL` through an injectable `getenv`, so tests and
applications can control the environment. Values passed explicitly win over
environment defaults.

Validation is strict: HTTPS-only base URLs (loopback HTTP is allowed for local
testing), no userinfo, query or fragment, a non-empty and injection-free API
key, positive finite timeouts, non-empty model names.

## Errors

Every fallible call returns `(_, Error.t) result`; nothing raises for a
transport or protocol failure. `Error.t` is a closed taxonomy, so a match on it
is exhaustive, and `Error.retryable` classifies a failure without re-deriving
the policy. Retries happen inside `Client.evaluate` and `Client.list_models`
according to `Retry.t`, so callers do not need a retry loop of their own.
`Error.message` renders a single-line description that never includes the API
key, and `Api` and `Decode` errors carry the server's `x-typesafe-request-id`
when it supplies one.

## Testing

```sh
opam exec -- dune runtest                # protocol, config, transport, retry
TYPESAFE_API_KEY=... VERDICT_LIVE_API=true opam exec -- dune runtest   # adds live smoke tests
```

The default suite runs entirely offline: real sockets against loopback servers,
`Eio_mock` for deterministic timing, and property tests for JSON round-tripping.
Live tests are a separate suite that is only built when `VERDICT_LIVE_API=true`,
so they never spend API credits by accident.

## Documentation

- API reference: `opam exec -- dune build @doc`, then open
  `_build/default/_doc/_html/verdict/index.html`.
- Worked examples: [`examples/`](examples)
- OpenAPI snapshot used for the wire format: [spec/openapi.json](spec/openapi.json)

## License

MIT. See [LICENSE](LICENSE).
