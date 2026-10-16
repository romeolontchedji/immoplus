// ESLint (format « flat ») : règles Expo + quelques garde-fous d'architecture (voir docs/architecture.md).
const expo = require("eslint-config-expo/flat");

module.exports = [
  ...expo,
  { ignores: ["dist/*", ".expo/*", "src/api/genere/*", "coverage/*"] },
  {
    rules: {
      "no-console": ["error", { allow: ["warn", "error"] }],
      // Une route (src/app) ne contient aucune logique : elle réexporte un écran de src/features.
      "no-restricted-imports": ["error", { patterns: [{ group: ["../../*", "../../../*"], message: "Utiliser l'alias @/ plutôt qu'un chemin relatif profond." }] }],
    },
  },
  {
    // Les doublures de modules natifs et le chargement tardif du client HTTP exigent `require`.
    files: ["jest.setup.ts", "src/__tests__/**"],
    rules: { "@typescript-eslint/no-require-imports": "off" },
  },
  {
    // Les fonctionnalités ne s'importent pas entre elles : elles passent par src/api, src/ui, src/lib ou src/state.
    files: ["src/features/**/*.{ts,tsx}"],
    rules: { "no-restricted-imports": ["error", { patterns: [{ group: ["@/app/*"], message: "Une fonctionnalité n'importe jamais une route." }] }] },
  },
];
