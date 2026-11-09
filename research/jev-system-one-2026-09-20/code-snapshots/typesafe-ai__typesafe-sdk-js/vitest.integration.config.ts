import { defineConfig } from "vitest/config";

/** Live API tests; `npm run test:integration` requires `TYPESAFE_API_KEY`. */
export default defineConfig({
  test: {
    include: ["test/integration/**/*.integration.ts"],
    testTimeout: 120_000,
    hookTimeout: 120_000,
  },
});
