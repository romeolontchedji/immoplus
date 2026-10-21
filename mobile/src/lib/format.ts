/** Mise en forme française : montants en FCFA, distances, dates, heures. Pure, testée. */
export function fcfa(montant: number): string {
  return `${Math.round(montant).toString().replace(/\B(?=(\d{3})+(?!\d))/g, "\u202F")} FCFA`;
}

/** Prix affiché comme sur le site et les maquettes : « 18 000 F ». */
export function francs(montant: number): string {
  return fcfa(montant).replace(/ FCFA$/, " F");
}

export function distance(metres: number): string {
  return metres >= 1000 ? `${(metres / 1000).toFixed(1).replace(".", ",")} km` : `${metres} m`;
}

const MOIS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."];

export function dateCourte(iso: string): string {
  const d = new Date(iso);
  return `${d.getDate()} ${MOIS[d.getMonth()] ?? ""} ${d.getFullYear()}`;
}

const deuxChiffres = (n: number) => String(n).padStart(2, "0");
export const heure = (iso: string): string => {
  const d = new Date(iso);
  return `${deuxChiffres(d.getHours())}:${deuxChiffres(d.getMinutes())}`;
};

/** « Aujourd'hui », « Hier » ou la date courte : en-têtes de jour dans une conversation. */
export function jourRelatif(iso: string, maintenant: Date = new Date()): string {
  const d = new Date(iso);
  const debut = (x: Date) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
  const ecart = Math.round((debut(maintenant) - debut(d)) / 86_400_000);
  if (ecart === 0) return "Aujourd'hui";
  if (ecart === 1) return "Hier";
  return dateCourte(iso);
}
