# Confidential OpenJev

An attestable, end-to-end encrypted deployment of [OpenJev](https://github.com/razorback16/openjev) on [Tinfoil Containers](https://docs.tinfoil.sh/containers/overview).

OpenJev is the closest currently available open reproduction of Jev's typed `POST /v1/systemone` contract. It reads `noul`, `choice`, and `score` answers directly from DiffusionGemma token probabilities instead of generating and parsing free-form text. The TypeSafe SDK can use the service by changing its base URL and keeping the `jev-latest` model alias.

This repository pins every executable input used by the enclave:

- OpenJev 0.2.0 by immutable OCI digest.
- DiffusionGemma 26B-A4B NVFP4 by immutable Hugging Face commit and Tinfoil dm-verity measurement.
- Tinfoil CVM version and GitHub Actions by immutable versions/commits.

The Tinfoil client verifies the enclave measurement before establishing its encrypted tunnel. Requests, bearer credentials, state, and model outputs are therefore encrypted to the attested enclave rather than merely to a conventional cloud load balancer.

## What "Jev-compatible" means

The acceptance contract is behavioral, not brand-level identity:

1. The current TypeSafe SDK can call the endpoint without changing request or response shapes.
2. The service returns calibrated distributions for all three Jev question types.
3. Errors, authentication, model aliases, and request IDs match the Jev wire contract.
4. A fixed target-domain corpus measures agreement, calibration, latency, and regressions against Jev.

Jev itself is proprietary, so bit-for-bit or universal semantic identity cannot be honestly guaranteed. OpenJev documents one known wire-level difference: choice questions support 128 options instead of Jev's 255. Domain agreement is measured after deployment rather than inferred from public benchmarks.

## Architecture

```text
TypeSafe SDK
    |
    | attestation-verified encrypted tunnel
    v
Tinfoil enclave shim :443
    |
    | loopback inside measured CVM
    v
OpenJev :8080 --> vLLM :8000 --> verified DiffusionGemma weights
```

The public shim routes only `/health` and `/v1/*`. OpenJev requires a bearer token for every `/v1/*` request. Tinfoil injects that token as an enclave secret; it is never committed to this repository.

## Release and deploy

Prerequisites: a Tinfoil organization with Containers and a confidential Blackwell GPU host enabled, the Tinfoil CLI, and GitHub CLI.

1. Wrap the exact model revision on the target Tinfoil host:

   ```bash
   tinfoil model wrap nvidia/diffusiongemma-26B-A4B-it-NVFP4 \
     --commit ec4ff3df205028f4e81c954c2227f9312b3ec2ea \
     --host <blackwell-host> --wait
   ```

2. Copy `tinfoil-config.template.yml` to `tinfoil-config.yml`, replacing both model placeholders with the values printed by `tinfoil model wrap`.

3. Create the `OPENJEV_API_KEY` Tinfoil secret, commit the final config, and push it.

4. Dispatch `Tinfoil Release` with an unused semantic version. The workflow tags the exact commit, measures the configuration, publishes its attestation, and creates the GitHub release.

5. Create the container from that release on the same host used to wrap the model.

6. Connect through the attesting Tinfoil client and run:

   ```bash
   OPENJEV_URL=http://127.0.0.1:8080 \
   OPENJEV_API_KEY=<client-key> \
   ./scripts/smoke.sh
   ```

## Updating

Treat the image digest, model commit/MPK, CVM version, and release tag as one measured release. Change pins deliberately, rerun the contract and target-domain evaluations, and publish a new tag. Never reuse a release tag.

## Security boundary

See [SECURITY.md](SECURITY.md) for the threat model and limits. Component provenance is recorded in [THIRD_PARTY.md](THIRD_PARTY.md).
