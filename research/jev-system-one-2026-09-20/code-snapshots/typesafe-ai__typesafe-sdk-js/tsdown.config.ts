import { defineConfig } from "tsdown";

export default defineConfig({
  entry: ["src/index.ts"],
  format: ["esm", "cjs"],
  platform: "neutral",
  target: "node20",
  dts: true,
  sourcemap: true,
  clean: true,
  fixedExtension: true,
});
