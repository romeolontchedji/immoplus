from django import forms

from apps.listings import selectors
from apps.listings.enums import Compteur, Eau
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
    water_source = forms.ChoiceField(label="Eau", choices=Eau.choices)
    electricity_meter = forms.ChoiceField(label="Compteur d'électricité", choices=Compteur.choices)
    description_md = forms.CharField(
        label="Description",
        required=False,
        max_length=6000,
        widget=forms.Textarea(
            attrs={
                "rows": 8,
                "placeholder": "Ce qui rend ta chambre agréable : calme, lumière, voisinage…",
            }
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
        for nom in ("has_private_bathroom", "is_fenced"):
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
