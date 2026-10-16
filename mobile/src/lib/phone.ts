/** Numéros du Bénin : saisie locale (8 chiffres, ou 10 avec le préfixe 01 des numéros récents) ↔ E.164 `+229…`. */
const PREFIXE = "+229";

export function chiffres(saisie: string): string {
  return saisie.replace(/\D/g, "");
}

/** Convertit une saisie en E.164, ou `null` si elle n'a pas la forme d'un numéro béninois. */
export function versE164(saisie: string): string | null {
  let n = chiffres(saisie);
  if (n.startsWith("00229")) n = n.slice(5);
  else if (n.startsWith("229") && n.length >= 11) n = n.slice(3);
  if (n.length === 8 || n.length === 10) return `${PREFIXE}${n}`;
  return null;
}

/** Affichage groupé par deux : « 97 12 34 56 ». */
export function formaterLocal(saisie: string): string {
  return chiffres(saisie).replace(/(\d{2})(?=\d)/g, "$1 ").trim();
}
