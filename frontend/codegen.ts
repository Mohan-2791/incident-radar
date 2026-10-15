import type { CodegenConfig } from "@graphql-codegen/cli";

// Types are generated from the backend's exported SDL (../schema.graphql),
// so a schema change that breaks the UI fails `tsc`, not production.
const config: CodegenConfig = {
  schema: "../schema.graphql",
  documents: ["src/**/*.{ts,tsx}"],
  ignoreNoDocuments: true,
  generates: {
    "src/gql/": {
      preset: "client",
      presetConfig: { fragmentMasking: false },
      config: { useTypeImports: true, enumsAsTypes: true },
    },
  },
};
export default config;
