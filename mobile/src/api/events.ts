/** Événements globaux de l'API que l'interface écoute : mise à jour obligatoire, maintenance, session perdue. */
type Evenement = "upgrade_required" | "maintenance" | "signed_out";
type Ecouteur = (detail?: string) => void;

const ecouteurs = new Map<Evenement, Set<Ecouteur>>();

export const apiEvents = {
  on(evenement: Evenement, ecouteur: Ecouteur): () => void {
    const ensemble = ecouteurs.get(evenement) ?? new Set<Ecouteur>();
    ensemble.add(ecouteur);
    ecouteurs.set(evenement, ensemble);
    return () => ensemble.delete(ecouteur);
  },
  emit(evenement: Evenement, detail?: string): void {
    ecouteurs.get(evenement)?.forEach((e) => e(detail));
  },
};
