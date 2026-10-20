from django import forms

from apps.listings import selectors
from apps.listings.enums import Compteur, Cuisine, Eau
from apps.listings.services import types

from .forms import _Base


class AnnonceForm(_Base):
    title = forms.CharField(label="Titre", max_length=120)
    room_type = forms.ChoiceField(label="Type de logement", required=False)
    nouveau_type = forms.CharField(
        label="Ou un autre type",
        max_length=40,
        required=False,
        help_text="Absent de la liste ? Écris-le : tu peux l'utiliser tout de suite, l'équipe le valide pour les filtres.",
        widget=forms.TextInput(attrs={"placeholder": "Ex. appartement meublé"}),
    )
    district = forms.ChoiceField(label="Quartier")
    landmark_text = forms.CharField(
        label="Repère public (ex. derrière la pharmacie)", max_length=160
    )
    address_private = forms.CharField(
        label="Adresse précise (visible seulement dans la conversation)",
        max_length=255,
        required=False,
    )
    rent_amount = forms.IntegerField(label="Loyer mensuel (FCFA)", min_value=1)
    rent_negotiable = forms.BooleanField(
        label="Prix à débattre", required=False,
        help_text="Coche si tu acceptes de discuter du loyer : la fiche affichera « à débattre ».",
    )  # fmt: skip
    deposit_months = forms.IntegerField(label="Caution (mois)", min_value=0, max_value=12)
    advance_months = forms.IntegerField(label="Avance (mois)", min_value=0, max_value=12)
    agent_fee_amount = forms.IntegerField(
        label="Frais de démarcheur (FCFA)", min_value=0, required=False, initial=0
    )
    available_from = forms.DateField(
        label="Disponible à partir du",
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )
    has_private_bathroom = forms.BooleanField(label="Douche et WC internes", required=False)
    is_fenced = forms.BooleanField(label="Clôture ou portail", required=False)
    electricity_meter = forms.ChoiceField(
        label="Électricité", choices=[("", "Choisis"), *Compteur.choices]
    )
    water_sources = forms.MultipleChoiceField(
        label="Eau",
        choices=Eau.choices,
        widget=forms.CheckboxSelectMultiple,
        help_text="Coche tout ce qui existe : forage, puits, compteur…",
        error_messages={"required": "Coche au moins une source d'eau."},
    )
    kitchen = forms.ChoiceField(label="Cuisine", choices=[("", "Choisis"), *Cuisine.choices])
    # « Autres détails » : texte simple, sans mise en forme (plan v3, C1).
    description_md = forms.CharField(
        label="Autres détails",
        required=False,
        max_length=4000,
        help_text="Ce que les champs ci-dessus ne disent pas : règles de la maison, voisinage, marché proche…",
        widget=forms.Textarea(
            attrs={"rows": 6, "placeholder": "Ex. Chambre au calme, à 5 minutes du marché Arzèkè."}
        ),
    )

    def __init__(self, *args, gerant=None, **kwargs):
        super().__init__(*args, **kwargs)
        proposes = types.pour_gerant(gerant) if gerant is not None else []
        self.fields["room_type"].choices = [("", "Choisis un type")] + [
            (
                t["slug"],
                t["label"] if t["status"] == "approved" else f"{t['label']} (en validation)",
            )
            for t in proposes
        ]
        self.fields["district"].choices = [
            (str(q.pk), q.name) for q in selectors.quartiers_actifs()
        ]
        for nom in ("has_private_bathroom", "is_fenced", "rent_negotiable"):
            self.fields[nom].widget.attrs.pop("class", None)

    def clean(self):
        d = super().clean()
        if not d.get("room_type") and not d.get("nouveau_type"):
            self.add_error("room_type", "Choisis un type, ou écris-en un nouveau.")
        return d

    def donnees(self) -> dict:
        d = dict(self.cleaned_data)
        d["agent_fee_amount"] = d.get("agent_fee_amount") or 0
        d["address_private"] = d.get("address_private") or ""
        d["description_md"] = d.get("description_md") or ""
        d.pop(
            "nouveau_type", None
        )  # traité par la vue (proposition du type), pas un champ d'annonce
        return d
