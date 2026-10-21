// Doublures des modules natifs : les tests s'exécutent sous Node, sans appareil.
jest.mock("expo-secure-store", () => {
  const magasin = new Map<string, string>();
  return {
    AFTER_FIRST_UNLOCK: 0,
    getItemAsync: jest.fn(async (k: string) => magasin.get(k) ?? null),
    setItemAsync: jest.fn(async (k: string, v: string) => void magasin.set(k, v)),
    deleteItemAsync: jest.fn(async (k: string) => void magasin.delete(k)),
    __magasin: magasin,
  };
});
jest.mock("@react-native-async-storage/async-storage", () => require("@react-native-async-storage/async-storage/jest/async-storage-mock"));
let mockCompteur = 0;
jest.mock("expo-crypto", () => ({ randomUUID: () => `00000000-0000-4000-8000-${String(++mockCompteur).padStart(12, "0")}` }));
