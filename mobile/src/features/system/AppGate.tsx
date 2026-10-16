import { useEffect, useState, type ReactNode } from "react";
import { apiEvents } from "@/api/events";
import { APP_VERSION } from "@/config/env";
import { estInferieure } from "@/lib/version";
import { MaintenanceScreen } from "./MaintenanceScreen";
import { MiseAJourScreen } from "./MiseAJourScreen";
import { useAppConfig } from "./useAppConfig";

/**
 * Barrière placée au-dessus de toute l'application : mise à jour obligatoire (version installée < `min_supported_version`
 * ou réponse 426) et maintenance (`maintenance.active` ou réponse 503). Pilotée par GET /v1/app-config, qui reste
 * joignable dans ces deux cas. En cas d'échec de lecture de la configuration, l'application continue (on ne bloque pas
 * l'utilisateur pour une panne de ce seul endpoint).
 */
export function AppGate({ children }: { children: ReactNode }) {
  const { data } = useAppConfig();
  const [forceMiseAJour, setForceMiseAJour] = useState(false);
  const [forceMaintenance, setForceMaintenance] = useState(false);

  useEffect(() => {
    const a = apiEvents.on("upgrade_required", () => setForceMiseAJour(true));
    const b = apiEvents.on("maintenance", () => setForceMaintenance(true));
    return () => {
      a();
      b();
    };
  }, []);

  if (forceMiseAJour || (data && estInferieure(APP_VERSION, data.min_supported_version))) return <MiseAJourScreen />;
  if (forceMaintenance || data?.maintenance.active) return <MaintenanceScreen message={data?.maintenance.message} />;
  return <>{children}</>;
}
