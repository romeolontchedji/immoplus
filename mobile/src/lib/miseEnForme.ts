/**
 * Markdown restreint des descriptions (décision V6, serveur : apps/listings/services/contenu.py) : gras, italique,
 * intertitre `### `, listes `- ` et `1. `. Mêmes règles que la barre du site (serveur/web/static/js/mise-en-forme.js).
 */

export type Format = "gras" | "italique" | "titre" | "liste" | "liste-numerotee";
export type Edition = { texte: string; debut: number; fin: number };

function entourer(texte: string, debut: number, fin: number, marque: string, exemple: string): Edition {
  const n = marque.length;
  if (texte.slice(debut - n, debut) === marque && texte.slice(fin, fin + n) === marque) {
    return { texte: texte.slice(0, debut - n) + texte.slice(debut, fin) + texte.slice(fin + n), debut: debut - n, fin: fin - n };
  }
  const contenu = texte.slice(debut, fin) || exemple;
  return { texte: texte.slice(0, debut) + marque + contenu + marque + texte.slice(fin), debut: debut + n, fin: debut + n + contenu.length };
}

function prefixer(texte: string, debut: number, fin: number, format: "titre" | "liste" | "liste-numerotee"): Edition {
  const d = texte.lastIndexOf("\n", debut - 1) + 1;
  let f = texte.indexOf("\n", fin);
  if (f === -1) f = texte.length;
  const motif = { titre: /^###\s/, liste: /^-\s/, "liste-numerotee": /^\d+\.\s/ }[format];
  const lignes = texte.slice(d, f).split("\n");
  const tous = lignes.every((l) => motif.test(l));
  const bloc = lignes
    .map((l, i) => {
      if (tous) return l.replace(motif, "");
      const nu = l.replace(/^(?:###\s|-\s|\d+\.\s)/, "");
      return (format === "titre" ? "### " : format === "liste" ? "- " : `${i + 1}. `) + nu;
    })
    .join("\n");
  return { texte: texte.slice(0, d) + bloc + texte.slice(f), debut: d, fin: d + bloc.length };
}

/** Applique un style à la sélection ; un second appui sur le même style le retire. */
export function appliquerFormat(format: Format, texte: string, debut: number, fin: number): Edition {
  if (format === "gras") return entourer(texte, debut, fin, "**", "texte en gras");
  if (format === "italique") return entourer(texte, debut, fin, "*", "texte en italique");
  return prefixer(texte, debut, fin, format);
}

// ------------------------------------------------------------------ lecture, pour l'affichage
export type Segment = { texte: string; gras?: boolean; italique?: boolean };
export type Bloc =
  | { type: "paragraphe"; segments: Segment[] }
  | { type: "titre"; segments: Segment[] }
  | { type: "liste"; ordonnee: boolean; elements: Segment[][] };

/** Gras `**…**` et italique `*…*` ou `_…_` dans une ligne (pas d'imbrication, comme le sous-ensemble du serveur). */
export function segments(ligne: string): Segment[] {
  const resultat: Segment[] = [];
  const motif = /\*\*([^*]+)\*\*|\*([^*]+)\*|_([^_]+)_/g;
  let curseur = 0;
  for (const m of ligne.matchAll(motif)) {
    const index = m.index ?? 0;
    if (index > curseur) resultat.push({ texte: ligne.slice(curseur, index) });
    if (m[1] !== undefined) resultat.push({ texte: m[1], gras: true });
    else resultat.push({ texte: m[2] ?? m[3] ?? "", italique: true });
    curseur = index + m[0].length;
  }
  if (curseur < ligne.length) resultat.push({ texte: ligne.slice(curseur) });
  return resultat;
}

/** Découpe le Markdown restreint en blocs : paragraphes (lignes consécutives), intertitres et listes. */
export function analyserMarkdown(md: string): Bloc[] {
  const blocs: Bloc[] = [];
  let paragraphe: string[] = [];
  const fermer = () => {
    if (paragraphe.length) blocs.push({ type: "paragraphe", segments: segments(paragraphe.join("\n")) });
    paragraphe = [];
  };
  for (const brute of (md ?? "").split("\n")) {
    const ligne = brute.trimEnd();
    const titre = /^#{1,6}\s+(.*)$/.exec(ligne);
    const puce = /^\s*[-*+]\s+(.*)$/.exec(ligne);
    const numero = /^\s*\d+[.)]\s+(.*)$/.exec(ligne);
    if (!ligne.trim()) {
      fermer();
    } else if (titre) {
      fermer();
      blocs.push({ type: "titre", segments: segments(titre[1] ?? "") });
    } else if (puce || numero) {
      fermer();
      const ordonnee = !!numero;
      const dernier = blocs[blocs.length - 1];
      const element = segments((puce ?? numero)?.[1] ?? "");
      if (dernier?.type === "liste" && dernier.ordonnee === ordonnee) dernier.elements.push(element);
      else blocs.push({ type: "liste", ordonnee, elements: [element] });
    } else {
      paragraphe.push(ligne);
    }
  }
  fermer();
  return blocs;
}
