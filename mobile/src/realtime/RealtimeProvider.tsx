import { createContext, useContext, useEffect, useMemo, useRef, type ReactNode } from "react";
import { AppState } from "react-native";
import { api, unwrap } from "@/api/client";
import { qk } from "@/api/keys";
import { WS_URL } from "@/config/env";
import { queryClient } from "@/state/queryClient";
import { useSession } from "@/state/session";
import { appliquerEvenement } from "./cache";
import { ClientTempsReel } from "./client";
import { definirFocusActuel } from "./focus";

type Valeur = { definirFocus: (conversationId: string | null) => void };
const Ctx = createContext<Valeur>({ definirFocus: () => undefined });

/**
 * Maintient le WebSocket tant que l'utilisateur est connecté ET l'application au premier plan : à l'arrière-plan la
 * connexion est coupée, ce qui efface la présence côté serveur (les push reprennent) — voir docs/mobile/websocket.md.
 */
export function RealtimeProvider({ children }: { children: ReactNode }) {
  const { etat } = useSession();
  const client = useRef<ClientTempsReel | null>(null);
  const focus = useRef<string | null>(null);
  const connecte = etat.statut === "connecte";

  useEffect(() => {
    if (!connecte) return;
    const c = new ClientTempsReel({
      url: WS_URL,
      ticket: async () => (await unwrap(api.POST("/v1/ws-ticket"))).ticket,
      surEvenement: appliquerEvenement,
      surOuverture: (premiere) => {
        // Rattrapage : à chaque connexion on relit ce qui a pu arriver pendant qu'on n'écoutait pas.
        void queryClient.invalidateQueries({ queryKey: qk.conversations });
        void queryClient.invalidateQueries({ queryKey: qk.notifications });
        void queryClient.invalidateQueries({ queryKey: qk.nonLues });
        if (!premiere) void queryClient.invalidateQueries({ queryKey: ["messages"] });
      },
    });
    client.current = c;
    c.definirFocus(focus.current);
    if (AppState.currentState === "active") c.demarrer();
    const abonnement = AppState.addEventListener("change", (s) => (s === "active" ? c.demarrer() : c.arreter()));
    return () => {
      abonnement.remove();
      c.arreter();
      client.current = null;
    };
  }, [connecte]);

  const valeur = useMemo<Valeur>(
    () => ({
      definirFocus: (id) => {
        focus.current = id;
        definirFocusActuel(id);
        client.current?.definirFocus(id);
      },
    }),
    [],
  );
  return <Ctx.Provider value={valeur}>{children}</Ctx.Provider>;
}

/** Annonce au serveur que cette conversation est à l'écran tant que le composant est monté (supprime le push pour cet appareil). */
export function useConversationFocus(conversationId: string | undefined): void {
  const { definirFocus } = useContext(Ctx);
  useEffect(() => {
    if (!conversationId) return;
    definirFocus(conversationId);
    return () => definirFocus(null);
  }, [conversationId, definirFocus]);
}
