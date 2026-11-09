# Generate the API reference

From the SDK source checkout, run:

```sh
npm run docs
```

This installs the locked documentation dependencies and generates Markdown
reference pages and `navigation.json` in `build/docs/`. No API key is needed.

To regenerate after editing source comments without reinstalling dependencies:

```sh
npm run --prefix docs build
```

TypeDoc reads the public exports from `src/index.ts` and their JSDoc comments.
Update the source comments to change the reference. Generated files are ignored
by Git, and generation fails on warnings.

The documentation toolchain uses TypeScript 6 because TypeDoc does not yet
support the SDK's TypeScript 7 compiler. Its dependencies are isolated in
`docs/`; the SDK build uses its own compiler.
