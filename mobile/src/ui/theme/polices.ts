/**
 * Police de l'application : Plus Jakarta Sans, la même que le site (licence OFL, assets/fonts/licence-…).
 * Une famille par graisse, extraite de la police variable du site : Android et iOS choisissent alors la bonne
 * graisse sans la simuler (texte net, lettres non coupées).
 */
export const POLICES = {
  "PlusJakartaSans-400": require("../../../assets/fonts/plus-jakarta-sans-400.ttf"),
  "PlusJakartaSans-500": require("../../../assets/fonts/plus-jakarta-sans-500.ttf"),
  "PlusJakartaSans-600": require("../../../assets/fonts/plus-jakarta-sans-600.ttf"),
  "PlusJakartaSans-700": require("../../../assets/fonts/plus-jakarta-sans-700.ttf"),
  "PlusJakartaSans-800": require("../../../assets/fonts/plus-jakarta-sans-800.ttf"),
} as const;

const NOMMEES: Record<string, number> = { thin: 100, ultralight: 200, light: 300, normal: 400, regular: 400, medium: 500, semibold: 600, condensedBold: 700, bold: 700, heavy: 800, black: 900 };

/** Famille correspondant à une graisse (`bold` = 700, au-delà de 800 = 800, en deçà de 400 = 400). */
export function familleDe(graisse: string | number | undefined): keyof typeof POLICES {
  const n = graisse === undefined ? 400 : (NOMMEES[String(graisse)] ?? (Number(graisse) || 400));
  const palier = Math.min(800, Math.max(400, Math.round(n / 100) * 100));
  return `PlusJakartaSans-${palier}` as keyof typeof POLICES;
}
