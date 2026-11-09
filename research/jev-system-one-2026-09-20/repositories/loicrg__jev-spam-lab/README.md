# jev-spam-lab

`jev-spam-lab` is a small Bun/TypeScript CLI experiment for testing whether
TypeSafe AI's Jev model can identify legitimate messages in Microsoft Outlook,
including messages that Outlook placed in Junk Email.

It is intentionally read-only. It never moves, deletes, restores, archives,
marks, categorizes, or sends mail.

## Prerequisites

- Bun 1.4 or newer
- A Microsoft Entra app registration with delegated Graph access
- Either a Vercel AI Gateway API key with access to `typesafe-ai/jev`, or an
  OpenRouter API key with access to `typesafe/jev-1.13`
- On Linux, `libsecret` is recommended for the secure MSAL cache used by
  `@azure/msal-node-extensions`

The Entra app registration must be configured as a **Mobile and desktop
application** with public client flows enabled and this redirect URI:

```text
http://localhost
```

The CLI opens the authorization URL in the system browser and listens on a
temporary loopback port for the callback. It is a public client, so it does
not use or require a client secret. The delegated Graph permissions requested
by the CLI are `User.Read` and `Mail.Read`.

The project uses Bun for the runtime, package manager, test runner, TypeScript
runner, `fetch`, and native SQLite.

## Configure Microsoft Entra ID

Sign in to the Azure tenant where you want to create the app registration:

```bash
az login
```

Create the public client with the localhost redirect URI:

```bash
JEV_APP_NAME="jev-spam-lab"
JEV_GRAPH_APP_ID="00000003-0000-0000-c000-000000000000"
JEV_USER_READ_PERMISSION_ID="e1fe6dd8-ba31-4d61-89e7-88639da4683d"
JEV_MAIL_READ_PERMISSION_ID="570282fd-fa5c-430d-a7fd-fc8dc98a9dca"
JEV_OWNER_OBJECT_ID="$(az ad signed-in-user show --query id --output tsv)"

JEV_CLIENT_ID="$(az ad app create \
  --display-name "$JEV_APP_NAME" \
  --sign-in-audience AzureADandPersonalMicrosoftAccount \
  --public-client-redirect-uris http://localhost \
  --is-fallback-public-client true \
  --query appId \
  --output tsv)"

az ad app owner add \
  --id "$JEV_CLIENT_ID" \
  --owner-object-id "$JEV_OWNER_OBJECT_ID"

printf 'MICROSOFT_CLIENT_ID=%s\n' "$JEV_CLIENT_ID"
```

Add the delegated Microsoft Graph permissions required by the CLI:

```bash
az ad app permission add \
  --id "$JEV_CLIENT_ID" \
  --api "$JEV_GRAPH_APP_ID" \
  --api-permissions \
    "$JEV_USER_READ_PERMISSION_ID=Scope" \
    "$JEV_MAIL_READ_PERMISSION_ID=Scope"
```

Verify the registration and confirm that it has no client credentials:

```bash
az ad app show \
  --id "$JEV_CLIENT_ID" \
  --query '{appId:appId,signInAudience:signInAudience,isFallbackPublicClient:isFallbackPublicClient,redirectUris:publicClient.redirectUris}' \
  --output json

az ad app credential list \
  --id "$JEV_CLIENT_ID" \
  --query 'length(@)' \
  --output tsv
```

The second command should print `0`. Use the printed client ID for
`MICROSOFT_CLIENT_ID` in the `.env` file after you run the install steps below.

If your tenant blocks user consent, an administrator can grant consent for the
delegated permissions:

```bash
az ad app permission admin-consent --id "$JEV_CLIENT_ID"
```

## Install

```bash
bun install
cp .env.example .env
```

Choose an evaluation provider and set its API key along with the Microsoft
Application (client) ID. Gateway remains the default:

```env
MICROSOFT_CLIENT_ID=your-entra-application-client-id
JEV_PROVIDER=gateway
AI_GATEWAY_API_KEY=your-vercel-ai-gateway-key
```

To use OpenRouter instead:

```env
JEV_PROVIDER=openrouter
OPENROUTER_API_KEY=your-openrouter-key
```

Optional `JEV_MODEL` overrides default to `typesafe-ai/jev` for Gateway and
`typesafe/jev-1.13` for OpenRouter. Other optional settings include
`SPAM_DB_PATH`, `SPAM_LOG_LEVEL`, and the three `POLICY_*_THRESHOLD` values
shown in `.env.example`.

## Run

Authenticate and verify the signed-in Microsoft account:

```bash
bun run spam login
```

`bun run spam auth` remains an alias for existing scripts.

Fetch and classify the latest 50 Junk Email messages (the default):

```bash
bun run spam scan
```

Check the latest messages in the Inbox instead:

```bash
bun run spam scan inbox
# equivalent:
bun run spam scan --folder inbox
```

Change the scan size or force re-evaluation:

```bash
bun run spam scan --limit 100
bun run spam scan inbox --limit 100
bun run spam scan --force
```

Review evaluated messages interactively:

```bash
bun run spam review
```

Use `L` for legitimate, `S` for spam, `F` for scam/phishing, `?` for unsure,
or `N` to leave a message unchanged. Reviews are stored locally and do not
modify Outlook.

Show the benchmark:

```bash
bun run spam stats
```

The policy is deliberately conservative:

- `LIKELY_LEGITIMATE`: legitimacy probability at least `0.97` and phishing
  probability at most `0.03`
- `REVIEW`: legitimacy probability at least `0.70` but not `LIKELY_LEGITIMATE`
- `LIKELY_SPAM`: everything else

The stats command treats `legitimate` as the positive ground-truth label,
excludes `unsure` from the confusion matrix, and reports precision, recall,
and false-rescue rate. The key experiment metric is the precision of
`LIKELY_LEGITIMATE`: when the tool says a scanned message is legitimate, how
often is that label correct?

## Data and privacy

The local SQLite database is stored at `data/jev-spam-lab.sqlite` by default.
It stores message metadata, a body hash, Jev probabilities, classifications,
and manual labels. It intentionally does not persist full message bodies.

The MSAL token cache is stored under `data/msal-cache/`, which is excluded from
Git. MSAL uses the operating system credential store where available; on Linux
without `libsecret`, its fallback is an owner-only (`0600`) cache file in an
owner-only (`0700`) directory.

The body sent to the selected Jev provider is capped at roughly 16 KiB after
normalization. Logs do not include access tokens or message bodies. The
application does not tell Jev which Outlook folder contained the source
message, so the model's assessment remains independent.

## Development

```bash
bun test
bun run typecheck
```

The test suite uses mocked/local inputs only; it does not call Microsoft Graph
or Jev.
