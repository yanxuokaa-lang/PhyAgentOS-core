import { defineConfig } from "vitest/config";

/** Built-package smoke tests; run `npm run build` before `npm run test:dist`. */
export default defineConfig({
  test: {
    include: ["test/dist/**/*.dist.ts"],
    typecheck: {
      enabled: true,
      include: ["test/dist/**/*.dist-d.ts"],
      tsconfig: "./tsconfig.dist-test.json",
    },
  },
});
