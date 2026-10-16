import { useNetInfo } from "@react-native-community/netinfo";

/** Vrai tant que le réseau est joignable ; `null` (inconnu) est traité comme « en ligne » pour ne pas alarmer à tort. */
export function useOnline(): boolean {
  const { isConnected, isInternetReachable } = useNetInfo();
  return isConnected !== false && isInternetReachable !== false;
}
