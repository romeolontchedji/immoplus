import { Upload } from "tus-js-client";
import { api, unwrap } from "@/api/client";
import { accessToken, installationId, refreshTokens } from "@/api/session";

/**
 * Envoi reprenable des photos et vidéos (docs/mobile/envoi-video-tus.md).
 * Le serveur crée l'envoi (`POST /v1/pro/listings/{id}/media` → `upload_url`) ; ensuite on envoie par morceaux de 1 Mo avec
 * le protocole tus : `HEAD` pour connaître le décalage, `PATCH` par morceau. Une coupure de réseau reprend là où elle s'est arrêtée.
 */
export const MORCEAU_OCTETS = 1024 * 1024; // le serveur accepte jusqu'à 2 Mo par morceau
const DELAIS_REPRISE_MS = [0, 1000, 3000, 5000, 10_000, 20_000];

export type Progression = (envoyes: number, total: number) => void;

/** Réduit la vidéo avant l'envoi (720p, MP4) : sur une connexion mobile, c'est ce qui rend l'envoi réaliste. */
/**
 * `react-native-compressor` repose sur Nitro, absent d'Expo Go : on le charge à la demande.
 * Si le module natif est indisponible (ou sous Expo Go), la vidéo est envoyée telle quelle
 * (le serveur gère l'encodage/reprise).
 */
async function chargerCompresseur(): Promise<typeof import("react-native-compressor") | null> {
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    return require("react-native-compressor") as typeof import("react-native-compressor");
  } catch {
    return null;
  }
}

export async function compresserVideo(uri: string, surProgression?: (ratio: number) => void): Promise<string> {
  const compresseur = await chargerCompresseur();
  if (!compresseur) return uri;
  return compresseur.Video.compress(uri, { compressionMethod: "auto" }, surProgression);
}

export async function envoyerFichier(o: { uploadUrl: string; uri: string; surProgression?: Progression; signal?: AbortSignal }): Promise<void> {
  const blob = await (await fetch(o.uri)).blob();
  const installation = await installationId();
  let renouvele = false;

  return new Promise<void>((resolve, reject) => {
    const envoi = new Upload(blob, {
      uploadUrl: o.uploadUrl, // créé par notre API : on ne passe pas par la création tus
      chunkSize: MORCEAU_OCTETS,
      retryDelays: DELAIS_REPRISE_MS,
      storeFingerprintForResuming: false, // la reprise se fait par HEAD sur l'URL, pas par empreinte locale
      removeFingerprintOnSuccess: true,
      onBeforeRequest: (requete) => {
        requete.setHeader("Authorization", `Bearer ${accessToken() ?? ""}`);
        requete.setHeader("X-Installation-Id", installation);
      },
      onProgress: (envoyes, total) => o.surProgression?.(envoyes, total),
      onSuccess: () => resolve(),
      onError: (erreur) => {
        const statut = (erreur as { originalResponse?: { getStatus(): number } }).originalResponse?.getStatus();
        if (statut === 401 && !renouvele) {
          renouvele = true; // jeton expiré pendant un long envoi : on le renouvelle une fois et on reprend
          void refreshTokens().then((ok) => (ok ? envoi.start() : reject(erreur)));
          return;
        }
        reject(erreur);
      },
    });
    o.signal?.addEventListener("abort", () => void envoi.abort());
    envoi.start();
  });
}

/**
 * Ajoute un média à une annonce : compresse la vidéo, déclare l'envoi au serveur (`kind`, `size_bytes` → `upload_url`),
 * puis envoie le fichier par morceaux. La progression va de 0 à 1.
 */
export async function ajouterMedia(o: { annonceId: string; uri: string; kind: "video" | "photo"; surProgression?: (ratio: number) => void }): Promise<void> {
  const uri = o.kind === "video" ? await compresserVideo(o.uri) : o.uri;
  const taille = (await (await fetch(uri)).blob()).size;
  const media = await unwrap(
    api.POST("/v1/pro/listings/{annonce_id}/media", { params: { path: { annonce_id: o.annonceId } }, body: { kind: o.kind, size_bytes: taille } }),
  );
  if (!media.upload_url) throw new Error("upload_url manquant");
  await envoyerFichier({ uploadUrl: media.upload_url, uri, surProgression: (envoyes, total) => o.surProgression?.(total ? envoyes / total : 0) });
}
