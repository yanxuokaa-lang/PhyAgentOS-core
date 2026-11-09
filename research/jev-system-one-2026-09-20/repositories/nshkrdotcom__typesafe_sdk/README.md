<p align="center">
  <img src="assets/typesafe_sdk.svg" alt="TypeSafeSDK" width="200" height="200"/>
</p>

# TypeSafeSDK

> ## This project has moved
>
> **Do not start new projects with `typesafe_sdk`.**
>
> TypeSafeSDK `0.4.1` is the final release of this package line.
>
> New development should use:
>
> # [`system_one_sdk`](https://github.com/nshkrdotcom/system_one_sdk)
>
> **Current release: `0.5.0`**
>
> `system_one_sdk` is the provider-neutral successor to this project and carries
> the semantic question API, prepared evaluations, typed answers, batching,
> telemetry, runtime controls, OTP integration, testing support, and decision
> tooling developed here.

---

## Package split

The functionality previously collected in TypeSafeSDK is now separated by
responsibility:

- **[`system_one_sdk`](https://github.com/nshkrdotcom/system_one_sdk)**
  The SDK application developers should use. It owns the provider-neutral
  System One programming model and higher-level Elixir/BEAM APIs.

- **[`typesafe_api_sdk`](https://github.com/nshkrdotcom/typesafe_api_sdk)**
  The TypeSafe-specific provider/API SDK. It owns TypeSafe authentication,
  endpoint and model configuration, generated wire operations, and TypeSafe API
  response handling.

`system_one_sdk` includes a built-in TypeSafe provider backed by
`typesafe_api_sdk`, so normal application code does not need to assemble these
layers manually.

---

## Existing TypeSafeSDK users

TypeSafeSDK `0.4.1` remains available as the final release for existing users,
but this repository is no longer the destination for new SDK development.

For migration and continued development, go to:

### **https://github.com/nshkrdotcom/system_one_sdk**

Historical implementation details, guides, examples, and release history remain
in this repository for reference.

---

## License

MIT License

Copyright (c) 2026 nshkrdotcom
