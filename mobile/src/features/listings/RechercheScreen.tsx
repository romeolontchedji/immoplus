import { useState } from "react";
import { View } from "react-native";
import { useRouter } from "expo-router";
import { sp } from "@/ui/theme/tokens";
import { Button } from "@/ui/components/Button";
import { Screen } from "@/ui/components/Screen";
import { TextField } from "@/ui/components/TextField";
import { nombreDeFiltres, useFiltres } from "./filtres";
import { ListeAnnonces } from "./ListeAnnonces";
import { useFil } from "./queries";

/** Onglet « Recherche » : texte libre (sans accents, tolérant aux fautes côté serveur) + filtres. Le vide propose de créer une alerte. */
export function RechercheScreen() {
  const router = useRouter();
  const { filtres, definir } = useFiltres();
  const [texte, setTexte] = useState(filtres.q);
  const requete = useFil(filtres);
  const n = nombreDeFiltres(filtres);
  return (
    <Screen flush>
      <View style={{ padding: sp[4], gap: sp[3] }}>
        <TextField label="Rechercher" value={texte} onChangeText={setTexte} onSubmitEditing={() => definir({ ...filtres, q: texte })} returnKeyType="search" placeholder="Quartier, repère, type…" />
        <Button titre={n ? `Filtres (${n})` : "Filtres"} variante="secondaire" onPress={() => router.push("/filtres")} />
      </View>
      <ListeAnnonces
        requete={requete}
        vide={{ titre: "Aucune chambre ne correspond", texte: "Élargis tes critères ou crée une alerte : tu seras prévenu dès qu'une chambre correspond.", action: "Créer une alerte", onAction: () => router.push("/nouvelle-alerte") }}
      />
    </Screen>
  );
}
