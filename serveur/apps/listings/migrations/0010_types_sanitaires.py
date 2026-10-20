"""Types de logement courants à Parakou (demande du porteur, 2026-10-20) : variantes simples et sanitaires.

« Sanitaire » : douche et toilettes dans la chambre ; « semi-sanitaire » : douche dedans, toilettes dehors.
Les slugs existants ne changent pas (annonces et alertes intactes) ; seuls leurs libellés sont précisés.
"""

from django.db import migrations

OFFICIELS = [
    ("single", "Chambre simple", 1),
    ("chambre_semi_sanitaire", "Chambre semi-sanitaire", 2),
    ("chambre_sanitaire", "Chambre sanitaire", 3),
    ("entree_coucher", "Entrée-couché simple", 4),
    ("entree_coucher_sanitaire", "Entrée-couché sanitaire", 5),
    ("chambre_salon", "Chambre-salon simple", 6),
    ("chambre_salon_sanitaire", "Chambre-salon sanitaire", 7),
    ("meuble_salon_sanitaire", "Meublé salon sanitaire", 8),
    ("studio", "Studio", 9),
    ("studio_meuble", "Studio meublé", 10),
    ("colocation", "Chambre en colocation", 11),
    ("residence_etudiante", "Chambre en résidence étudiante", 12),
    ("appartement_2_chambres", "Appartement 2 chambres salon", 13),
    ("appartement_3_chambres", "Appartement 3 chambres salon et plus", 14),
    ("appartement_meuble", "Appartement meublé", 15),
    ("maison", "Maison individuelle", 16),
    ("duplex", "Duplex", 17),
    ("villa", "Villa", 18),
]
NOUVEAUX = [
    "chambre_semi_sanitaire",
    "chambre_sanitaire",
    "entree_coucher_sanitaire",
    "chambre_salon_sanitaire",
    "meuble_salon_sanitaire",
]
ANCIENS = [  # libellés et ordre de la migration 0004
    ("single", "Chambre simple", 1),
    ("entree_coucher", "Entrée-coucher", 2),
    ("chambre_salon", "Chambre-salon", 3),
    ("studio", "Studio", 4),
    ("studio_meuble", "Studio meublé", 5),
    ("colocation", "Chambre en colocation", 6),
    ("residence_etudiante", "Chambre en résidence étudiante", 7),
    ("appartement_2_chambres", "Appartement 2 chambres salon", 8),
    ("appartement_3_chambres", "Appartement 3 chambres salon et plus", 9),
    ("appartement_meuble", "Appartement meublé", 10),
    ("maison", "Maison individuelle", 11),
    ("duplex", "Duplex", 12),
    ("villa", "Villa", 13),
]


def _appliquer(apps, liste):
    RoomType = apps.get_model("listings", "RoomType")
    for slug, label, ordre in liste:
        RoomType.objects.update_or_create(
            slug=slug, defaults={"label": label, "status": "approved", "sort_order": ordre}
        )


def creer(apps, schema_editor):
    _appliquer(apps, OFFICIELS)


def retirer(apps, schema_editor):
    RoomType = apps.get_model("listings", "RoomType")
    Listing = apps.get_model("listings", "Listing")
    utilises = set(
        Listing.objects.filter(room_type__in=NOUVEAUX).values_list("room_type", flat=True)
    )
    RoomType.objects.filter(slug__in=set(NOUVEAUX) - utilises, proposed_by__isnull=True).delete()
    _appliquer(apps, ANCIENS)


class Migration(migrations.Migration):
    dependencies = [
        ("listings", "0009_equipements_prix_avis"),
    ]

    operations = [migrations.RunPython(creer, retirer)]
