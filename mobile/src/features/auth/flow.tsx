import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

/** État partagé par les étapes d'un parcours à code (numéro → code → suite) : en mémoire seulement, jamais persisté. */
type Etat = { phone: string | null; otpToken: string | null };
type Valeur = Etat & { definirTelephone: (e164: string) => void; definirJeton: (jeton: string) => void; reinitialiser: () => void };

const Ctx = createContext<Valeur | null>(null);

export function AuthFlowProvider({ children }: { children: ReactNode }) {
  const [etat, setEtat] = useState<Etat>({ phone: null, otpToken: null });
  const valeur = useMemo<Valeur>(
    () => ({
      ...etat,
      definirTelephone: (phone) => setEtat({ phone, otpToken: null }),
      definirJeton: (otpToken) => setEtat((e) => ({ ...e, otpToken })),
      reinitialiser: () => setEtat({ phone: null, otpToken: null }),
    }),
    [etat],
  );
  return <Ctx.Provider value={valeur}>{children}</Ctx.Provider>;
}

export function useAuthFlow(): Valeur {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAuthFlow doit être utilisé dans <AuthFlowProvider>.");
  return v;
}
