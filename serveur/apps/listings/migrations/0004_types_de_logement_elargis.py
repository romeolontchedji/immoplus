"""Types de logement officiels élargis (demande du porteur, 2026-10-17) : de la chambre simple à la villa.

Un gérant doit presque toujours trouver son type dans la liste ; « Autre type » reste possible (décision V1).
Un slug déjà proposé par un gérant devient officiel (validé), sans toucher aux annonces qui le portent.
"""

from django.db import migrations

OFFICIELS = [
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
NOUVEAUX = [slug for slug, _, ordre in OFFICIELS if ordre > 4]


def creer(apps, schema_editor):
    RoomType = apps.get_model("listings", "RoomType")
    for slug, label, ordre in OFFICIELS:
        RoomType.objects.update_or_create(
            slug=slug, defaults={"label": label, "status": "approved", "sort_order": ordre}
        )


def retirer(apps, schema_editor):
    RoomType = apps.get_model("listings", "RoomType")
    Listing = apps.get_model("listings", "Listing")
    utilises = set(
        Listing.objects.filter(room_type__in=NOUVEAUX).values_list("room_type", flat=True)
    )
    RoomType.objects.filter(slug__in=set(NOUVEAUX) - utilises, proposed_by__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("listings", "0003_types_de_logement"),
    ]

    operations = [migrations.RunPython(creer, retirer)]
