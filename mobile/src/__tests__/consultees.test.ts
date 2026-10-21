jest.mock("@/storage/kv", () => ({ CLES_KV: { consultees: "c" }, kv: { get: jest.fn(async () => null), set: jest.fn(async () => undefined) } }));

import { _consultees, effacerConsultees, noterConsultation } from "@/features/listings/consultees";

const c = (slug: string) => ({ slug, title: slug, rent_amount: 10000, district: "Banikanni" });

describe("chambres consultées", () => {
  beforeEach(() => effacerConsultees());

  it("remonte une chambre revue en tête sans doublon", () => {
    noterConsultation(c("a"));
    noterConsultation(c("b"));
    noterConsultation(c("a"));
    expect(_consultees.lire().map((x) => x.slug)).toEqual(["a", "b"]);
  });

  it("garde au plus huit chambres", () => {
    for (let i = 0; i < 12; i++) noterConsultation(c(`s${i}`));
    expect(_consultees.lire()).toHaveLength(_consultees.max);
    expect(_consultees.lire()[0]?.slug).toBe("s11");
  });
});
