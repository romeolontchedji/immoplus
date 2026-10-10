"""Données de départ : paramètres, quartiers de Parakou et, en développement seulement, un jeu de démonstration.

Les coordonnées des quartiers sont **approximatives** : elles servent au calcul de distance et à la carte, et
doivent être relevées sur le terrain avant la mise en production (voir docs/a-verifier.md).
"""

import datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.accounts.models import GerantProfile, Role, StatutVerification, User
from apps.core import parametres
from apps.core.models import AppSetting
from apps.listings.models import District, Listing
from apps.listings.services import annonces

# (nom, slug, latitude, longitude) — points approximatifs, à relever.
QUARTIERS = [
    ("Banikanni", "banikanni", "9.3420", "2.6280"),
    ("Titirou", "titirou", "9.3380", "2.6350"),
    ("Zongo", "zongo", "9.3490", "2.6200"),
    ("Albarika", "albarika", "9.3300", "2.6420"),
    ("Madina", "madina", "9.3450", "2.6100"),
    ("Arafat", "arafat", "9.3250", "2.6150"),
    ("Ganou", "ganou", "9.3550", "2.6300"),
    ("Kpébié", "kpebie", "9.3200", "2.6300"),
    ("Guéma", "guema", "9.3600", "2.6450"),
    ("Ladjifarani", "ladjifarani", "9.3350", "2.6000"),
    ("Tourou", "tourou", "9.3700", "2.6150"),
    ("Wansirou", "wansirou", "9.3150", "2.6500"),
]

DEMO = [
    ("Chambre propre avec douche interne", "single", "banikanni", 25000, True, True, 450),
    ("Studio moderne près du campus", "studio", "titirou", 40000, True, True, 600),
    ("Chambre simple, quartier calme", "single", "zongo", 15000, False, True, 1200),
    ("Chambre avec cour et portail", "single", "albarika", 20000, False, True, 1500),
    ("Studio avec eau courante", "studio", "madina", 35000, True, False, 2100),
    ("Chambre-salon pour deux étudiants", "chambre_salon", "arafat", 45000, True, True, 1800),
]


class Command(BaseCommand):
    help = "Crée les paramètres, les quartiers de Parakou et, avec --demo (développement), des annonces d'exemple."

    def add_arguments(self, parser):
        parser.add_argument(
            "--demo", action="store_true", help="Ajoute un gérant et des annonces de démonstration."
        )

    def handle(self, *args, **options):
        self._parametres()
        self._quartiers()
        if options["demo"]:
            if not settings.DEBUG:
                raise CommandError("Le jeu de démonstration est réservé au développement (DEBUG).")
            self._demonstration()

    def _parametres(self):
        crees = 0
        for cle, (valeur, description) in parametres.DEFAUTS.items():
            _, cree = AppSetting.objects.get_or_create(
                key=cle, defaults={"value": valeur, "description": description}
            )
            crees += int(cree)
        self.stdout.write(
            f"Paramètres : {crees} créé(s), {len(parametres.DEFAUTS) - crees} déjà présent(s)."
        )

    def _quartiers(self):
        crees = 0
        for ordre, (nom, slug, lat, lon) in enumerate(QUARTIERS):
            _, cree = District.objects.get_or_create(
                slug=slug,
                defaults={"name": nom, "latitude": lat, "longitude": lon, "sort_order": ordre},
            )
            crees += int(cree)
        self.stdout.write(f"Quartiers : {crees} créé(s), {len(QUARTIERS) - crees} déjà présent(s).")

    def _demonstration(self):
        admin, _ = User.objects.get_or_create(
            email="demo-admin@logeo.test",
            defaults={
                "full_name": "Admin démo",
                "role": Role.ADMIN,
                "phone_e164": "+22901970000099",
            },
        )
        gerant, cree = User.objects.get_or_create(
            phone_e164="+22901970000001", defaults={"full_name": "Aïcha Démo", "role": Role.GERANT}
        )
        if cree:
            gerant.set_unusable_password()
            gerant.save()
        profil = GerantProfile.complets.filter(pk=gerant.pk).first()
        if profil is None:
            profil = GerantProfile.complets.create(user=gerant, zone="Banikanni", created_by=admin)
        GerantProfile.complets.filter(pk=gerant.pk).update(
            verification_status=StatutVerification.VERIFIED, verified_at=timezone.now()
        )
        quartiers = {d.slug: d for d in District.objects.all()}
        crees = 0
        for titre, type_, slug, loyer, douche, cloture, distance in DEMO:
            if Listing.objects.filter(title=titre, gerant=profil).exists():
                continue
            district = quartiers[slug]
            annonce = Listing(
                gerant=profil, title=titre, room_type=type_, district=district,
                landmark_text=f"Près du marché de {district.name}", address_private="Adresse de démonstration",
                latitude=district.latitude, longitude=district.longitude, rent_amount=loyer,
                deposit_months=2, advance_months=1, available_from=datetime.date.today() + datetime.timedelta(days=15),
                has_private_bathroom=douche, is_fenced=cloture, water_source="running",
                electricity_meter="individual", description_md=f"{titre}. Idéal pour un étudiant.\n\n- Calme\n- Bien situé",
                description_html=f"<p>{titre}. Idéal pour un étudiant.</p><ul><li>Calme</li><li>Bien situé</li></ul>",
                distance_to_campus_m=distance, status="published", published_at=timezone.now(),
                last_confirmed_at=timezone.now(), slug=annonces._slug(titre),
            )  # fmt: skip
            annonce.save()
            annonces._vecteur_de_recherche(annonce)
            crees += 1
        self.stdout.write(
            f"Démonstration : {crees} annonce(s) créée(s) (sans média ; compte gérant +22901970000001)."
        )
