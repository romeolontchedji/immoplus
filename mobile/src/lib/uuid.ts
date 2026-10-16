import * as Crypto from "expo-crypto";

/** Identifiant aléatoire (UUID v4) : `client_msg_id` des messages, identifiant d'installation. */
export function newId(): string {
  return Crypto.randomUUID();
}
