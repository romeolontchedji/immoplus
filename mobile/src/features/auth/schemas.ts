import { z } from "zod";
import { versE164 } from "@/lib/phone";

/** Validation côté appareil, pour réagir vite. Le serveur reste l'autorité : ses erreurs de champ sont réaffichées telles quelles. */
export const telephone = z.string().refine((v) => versE164(v) !== null, "Numéro invalide (8 chiffres, Bénin).");
export const motDePasse = z.string().min(8, "8 caractères au moins.").max(128, "128 caractères au plus.");

export const connexionSchema = z.object({ phone: telephone, password: z.string().min(1, "Obligatoire.") });
export const telephoneSchema = z.object({ phone: telephone });
export const codeSchema = z.object({ code: z.string().regex(/^\d{6}$/, "Le code a 6 chiffres.") });
export const profilSchema = z.object({
  full_name: z.string().trim().min(2, "Au moins 2 caractères.").max(80, "80 caractères au plus."),
  password: motDePasse,
});
export const nouveauMotDePasseSchema = z.object({ new_password: motDePasse });
