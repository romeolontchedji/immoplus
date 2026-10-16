/** Compare deux versions numériques « 1.10.2 » (par composante, pas alphabétiquement). Une version illisible n'est jamais « trop ancienne ». */
function composantes(v: string): number[] | null {
  const morceaux = v.trim().split(".").map((x) => Number(x));
  return morceaux.length > 0 && morceaux.every((n) => Number.isInteger(n) && n >= 0) ? morceaux : null;
}

export function estInferieure(installee: string, minimale: string): boolean {
  const a = composantes(installee);
  const b = composantes(minimale);
  if (!a || !b) return false;
  for (let i = 0; i < Math.max(a.length, b.length); i++) {
    const x = a[i] ?? 0;
    const y = b[i] ?? 0;
    if (x !== y) return x < y;
  }
  return false;
}
