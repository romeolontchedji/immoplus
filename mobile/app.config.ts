import type { ExpoConfig } from "expo/config";

/**
 * Configuration Expo de Immo+ (une seule application, deux espaces : locataire et gérant).
 * Les valeurs qui changent selon l'environnement viennent de `EXPO_PUBLIC_*` (voir `.env.example`).
 */
const hoteWeb = process.env.EXPO_PUBLIC_WEB_HOST ?? "immoplus.example"; // domaine du site : liens profonds https

const config: ExpoConfig = {
  name: "Immo+",
  slug: "immoplus",
  scheme: "immoplus", // liens profonds : immoplus://annonces/<slug>
  version: "1.0.0", // doit rester >= `min_supported_version` renvoyée par GET /v1/app-config
  orientation: "portrait",
  icon: "./assets/icon.png",
  userInterfaceStyle: "light", // thème clair uniquement (le sombre rendait des textes illisibles)
  android: {
    package: "bj.immoplus.app", // à confirmer avant la première publication (impossible à changer ensuite)
    adaptiveIcon: {
      backgroundColor: "#1B44D6", // bleu Immo+
      foregroundImage: "./assets/android-icon-foreground.png",
      backgroundImage: "./assets/android-icon-background.png",
      monochromeImage: "./assets/android-icon-monochrome.png",
    },
    permissions: ["POST_NOTIFICATIONS", "ACCESS_FINE_LOCATION", "CAMERA", "READ_MEDIA_IMAGES", "READ_MEDIA_VIDEO"],
    intentFilters: [
      {
        action: "VIEW",
        autoVerify: true, // exige https://<hote>/.well-known/assetlinks.json (servi par Caddy)
        data: [{ scheme: "https", host: hoteWeb, pathPrefix: "/annonces" }],
        category: ["BROWSABLE", "DEFAULT"],
      },
    ],
  },
  ios: { supportsTablet: false, bundleIdentifier: "bj.immoplus.app" },
  plugins: [
    "expo-router",
    "expo-secure-store",
    "expo-video",
    "expo-image",
    "expo-localization",
    ["expo-splash-screen", { image: "./assets/splash-icon.png", imageWidth: 200, resizeMode: "contain", backgroundColor: "#FFFFFF" }],
    ["expo-build-properties", { android: { minSdkVersion: 26 } }], // Android 8.0 (ENF-COMP-01)
    ["expo-notifications", { color: "#117853" }],
    ["expo-image-picker", { photosPermission: "Immo+ accède à tes photos pour illustrer ton annonce.", cameraPermission: "Immo+ utilise la caméra pour filmer ta chambre." }],
    ["expo-location", { locationWhenInUsePermission: "Immo+ utilise ta position pour situer ta chambre sur la carte." }],
    ["expo-local-authentication", { faceIDPermission: "Immo+ utilise Face ID pour déverrouiller l'application." }], // ADR 0005
    "react-native-compressor",
  ],
  experiments: { reactCompiler: false },
  extra: {
    eas: { projectId: process.env.EAS_PROJECT_ID ?? "" }, // renseigné après `eas init`
  },
  updates: { fallbackToCacheTimeout: 0 }, // EAS Update : correctifs JavaScript sans repasser par le magasin
  runtimeVersion: { policy: "appVersion" },
};

export default config;
