import { FILTRES_VIDES, filtresActifs, nombreDeFiltres, versParametres } from "@/features/listings/filtres";
import { criteresDepuisFiltres, resumeCriteres, CRITERES_VIDES } from "@/features/alerts/EditeurCriteres";
import { francs } from "@/lib/format";
import { urlMedia } from "@/lib/media";
import { API_URL } from "@/config/env";

jest.mock("lucide-react-native", () => ({}));
jest.mock("@react-native-community/netinfo", () => require("@react-native-community/netinfo/jest/netinfo-mock.js"));

describe("recherche", () => {
  const f = { ...FILTRES_VIDES, district: ["banikanni"], type: ["studio"], water: ["borehole"], rent_max: 15000, bathroom: true };

  it("liste chaque filtre actif, retirable un par un", () => {
    const actifs = filtresActifs(f, { banikanni: "Banikanni" }, (t) => t.toUpperCase());
    expect(actifs.map((a) => a.libelle)).toEqual(["Banikanni", "STUDIO", "Forage", "≤ 15 000 F", "Douche interne"]);
    const sansBudget = actifs.find((a) => a.cle === "budget")!.retirer(f);
    expect(sansBudget.rent_max).toBeUndefined();
    expect(sansBudget.district).toEqual(["banikanni"]);
  });

  it("compte et transmet la source d'eau", () => {
    expect(nombreDeFiltres(f)).toBe(5);
    expect(versParametres(f).water).toBe("borehole");
  });

  it("affiche les prix en F", () => expect(francs(18000)).toBe("18 000 F"));

  it("rattache les médias relatifs à l'hôte de l'API", () => {
    expect(urlMedia("/media/a.webp")).toBe(`${API_URL}/media/a.webp`);
    expect(urlMedia("https://cdn.example/a.webp")).toBe("https://cdn.example/a.webp");
    expect(urlMedia(null)).toBeUndefined();
  });

  it("transforme la recherche en critères d'alerte (slug → identifiant)", () => {
    const c = criteresDepuisFiltres(f, [{ id: "uuid-b", slug: "banikanni" }, { id: "uuid-t", slug: "titirou" }]);
    expect(c).toEqual({
      ...CRITERES_VIDES, district_ids: ["uuid-b"], room_types: ["studio"], max_rent: 15000, private_bathroom_required: true,
      water_sources: ["borehole"], // l'eau de la recherche suit dans l'alerte (2026-10-20)
    });
    expect(resumeCriteres(c, { "uuid-b": "Banikanni" }).titre).toBe("Banikanni · Studio");
  });

  it("affiche le libellé d'un type venu du serveur (décision V1)", () => {
    const c = { ...CRITERES_VIDES, room_types: ["villa", "inconnu"] };
    expect(resumeCriteres(c, {}, [{ slug: "villa", label: "Villa" }]).titre).toContain("Villa, inconnu");
  });
});
