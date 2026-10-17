import { analyserMarkdown, appliquerFormat, segments } from "@/lib/miseEnForme";

describe("appliquerFormat", () => {
  it("met la sélection en gras puis retire le gras au second appui", () => {
    const a = appliquerFormat("gras", "Chambre calme", 8, 13);
    expect(a).toEqual({ texte: "Chambre **calme**", debut: 10, fin: 15 });
    expect(appliquerFormat("gras", a.texte, a.debut, a.fin)).toEqual({ texte: "Chambre calme", debut: 8, fin: 13 });
  });

  it("insère un exemple sélectionné quand rien n'est sélectionné", () => {
    const a = appliquerFormat("italique", "", 0, 0);
    expect(a.texte).toBe("*texte en italique*");
    expect(a.texte.slice(a.debut, a.fin)).toBe("texte en italique");
  });

  it("transforme les lignes sélectionnées en liste numérotée, puis les remet en texte", () => {
    const texte = "Intro\nDouche\nCour";
    const a = appliquerFormat("liste-numerotee", texte, 7, texte.length);
    expect(a.texte).toBe("Intro\n1. Douche\n2. Cour");
    expect(appliquerFormat("liste-numerotee", a.texte, a.debut, a.fin).texte).toBe(texte);
  });

  it("remplace une puce par un numéro au lieu de les cumuler", () => {
    expect(appliquerFormat("liste-numerotee", "- Douche", 0, 0).texte).toBe("1. Douche");
  });

  it("pose un intertitre sur la ligne du curseur", () => {
    expect(appliquerFormat("titre", "Le quartier\nCalme", 3, 3).texte).toBe("### Le quartier\nCalme");
  });
});

describe("analyserMarkdown", () => {
  it("lit paragraphes, intertitres et listes", () => {
    const blocs = analyserMarkdown("Chambre **calme** et *lumineuse*\n\n### Équipements\n- Douche\n- Cour\n1. Un");
    expect(blocs.map((b) => b.type)).toEqual(["paragraphe", "titre", "liste", "liste"]);
    expect(blocs[0]).toEqual({
      type: "paragraphe",
      segments: [{ texte: "Chambre " }, { texte: "calme", gras: true }, { texte: " et " }, { texte: "lumineuse", italique: true }],
    });
    expect(blocs[2]).toMatchObject({ ordonnee: false, elements: [[{ texte: "Douche" }], [{ texte: "Cour" }]] });
    expect(blocs[3]).toMatchObject({ ordonnee: true });
  });

  it("laisse le texte sans marque tel quel", () => {
    expect(segments("Prix : 25 000 F")).toEqual([{ texte: "Prix : 25 000 F" }]);
    expect(analyserMarkdown("")).toEqual([]);
  });
});
