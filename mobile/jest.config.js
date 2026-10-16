module.exports = {
  preset: "jest-expo",
  testMatch: ["**/__tests__/**/*.test.ts?(x)"],
  moduleNameMapper: { "^@/(.*)$": "<rootDir>/src/$1" },
  setupFiles: ["<rootDir>/jest.setup.ts"],
  // Le seuil porte sur la logique testée sans appareil : client HTTP, session, temps réel, stockage, utilitaires, règles pures des
  // fonctionnalités. Les crochets de données (`queries.ts`, `hooks.ts`) et les écrans relèvent des tests de composants et des
  // parcours Maestro (voir docs/tests.md) et ne sont pas comptés ici.
  collectCoverageFrom: [
    "src/api/{client,errors,events,session}.ts", "src/realtime/{client,events,cache}.ts", "src/storage/{kv,outbox}.ts", "src/lib/*.ts",
    "src/features/notifications/routage.ts", "src/features/listings/filtres.tsx", "src/features/pro/brouillon.tsx",
  ],
  coverageThreshold: { global: { statements: 70, branches: 60, functions: 70, lines: 70 } },
};
