import { familleDe } from "@/ui/theme/polices";

describe("police de l'application", () => {
  it("associe chaque graisse à sa famille, bornée entre 400 et 800", () => {
    expect(familleDe("800")).toBe("PlusJakartaSans-800");
    expect(familleDe("bold")).toBe("PlusJakartaSans-700");
    expect(familleDe(undefined)).toBe("PlusJakartaSans-400");
    expect(familleDe("300")).toBe("PlusJakartaSans-400");
    expect(familleDe(900)).toBe("PlusJakartaSans-800");
    expect(familleDe("medium")).toBe("PlusJakartaSans-500");
  });
});
