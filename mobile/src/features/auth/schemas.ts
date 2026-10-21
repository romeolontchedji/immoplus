import { z } from "zod";

/** Validation côté appareil, pour réagir vite. Le serveur reste l'autorité : ses erreurs de champ sont réaffichées telles quelles. */
export const motDePasse = z.string().min(10, "10 caractères au moins.").max(128, "128 caractères au plus.");
/** Nom d'utilisateur (ADR 0009) : la forme seulement ; la disponibilité et les noms réservés sont vérifiés par le serveur. */
export const nomUtilisateur = z
  .string()
  .trim()
  .transform((v) => v.replace(/^@/, "").toLowerCase())
  .pipe(z.string().regex(/^[a-z0-9][a-z0-9._]{1,28}[a-z0-9]$/, "3 à 30 caractères : lettres, chiffres, point ou tiret bas."));
const nom = (libelle: string) => z.string().trim().min(1, `Indique ton ${libelle}.`).max(60, "60 caractères au plus.");

export const connexionSchema = z.object({ username: z.string().trim().min(1, "Obligatoire."), password: z.string().min(1, "Obligatoire.") });
export const inscriptionSchema = z.object({
  first_name: nom("prénom"),
  last_name: nom("nom"),
  username: nomUtilisateur,
  password: motDePasse,
  terms_accepted: z.literal(true, { error: "Accepte les conditions pour continuer." }),
});
export const lienEmailSchema = z.object({ identifier: z.string().trim().min(3, "Nom d'utilisateur ou e-mail.") });
export const cleSchema = z.object({
  username: nomUtilisateur,
  recovery_key: z.string().trim().regex(/^[A-Za-z0-9]{4}-?[A-Za-z0-9]{4}-?[A-Za-z0-9]{4}-?[A-Za-z0-9]{4}$/, "16 caractères, ex. K7QM-2XPA-9RTD-H4WN."),
  new_password: motDePasse,
});
export const nouveauMotDePasseSchema = z.object({ new_password: motDePasse });
