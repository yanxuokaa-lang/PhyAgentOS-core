# 🪨 `von-sdk`

**Official TypeScript & JavaScript SDK for Von — The Open-Source System One Decision Model.**  
*Drop-in replacement for `@typesafe-ai/sdk`.*

---

## Installation

```bash
# Using Bun (Recommended)
bun add von-sdk

# Using npm / pnpm / yarn
npm install von-sdk
```

---

## Migration from `@typesafe-ai/sdk`

If you are migrating from TypeSafe Jev, simply change the import statement:

```typescript
// Before:
// import { TypeSafeClient, choice, noul, score } from "@typesafe-ai/sdk";

// After (drop-in alias):
import { TypeSafeClient, choice, noul, score } from "von-sdk";

const client = new TypeSafeClient({ baseURL: "http://localhost:8000" });
```

---

## Quickstart

```typescript
import { VonClient, choice, noul, score } from "von-sdk";

const client = new VonClient({
  baseURL: process.env.VON_BASE_URL || "http://localhost:8000",
  apiKey: process.env.VON_API_KEY, // Optional bearer auth
});

// 1. Multi-question Fan-out
const response = await client.systemOne({
  state: "Customer asks for an immediate refund on duplicate invoice charge #401",
  questions: {
    department: choice("Which department should handle this?", {
      billing: "Invoices, refunds, payments",
      tech: "Software bugs, outages",
    }),
    isUrgent: noul("Does the request communicate time pressure?"),
    frustration: score("Rate the user frustration level", [
      "Calm",
      "Concerned",
      "Very angry",
    ]),
  },
});

console.log(response.answers.department.choice);     // "billing"
console.log(response.answers.department.confidence); // 0.92
console.log(response.answers.isUrgent.noul);         // 0.88

// 2. Fast Discrete Decision Helper
const routing = await client.decide(
  "Server CPU temperature reached 105 degrees Celsius",
  { hardware: "Hardware/temperature issue", software: "Application bug" }
);
console.log(routing.choice); // "hardware"

// 3. Binary Verification Helper (Noul)
const isOutage = await client.judge(
  "Database connection pool exhausted on port 5432",
  "Is the database down or failing?"
);
console.log(isOutage); // 0.9412
```

---

## License

Apache-2.0
