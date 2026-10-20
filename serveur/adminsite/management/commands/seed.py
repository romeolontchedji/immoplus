"""Données de départ : paramètres, quartiers de Parakou et, en développement seulement, un jeu de démonstration complet.

Les coordonnées des quartiers sont approximatives : elles servent au calcul de distance et à la carte, et
doivent être relevées sur le terrain avant la mise en production (voir docs/a-verifier.md).
"""

import datetime
import uuid

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from PIL import Image, ImageDraw

from apps.accounts.models import GerantProfile, Role, StatutVerification, User
from apps.chat.models import Conversation, Message
from apps.core import parametres
from apps.core.models import AppSetting
from apps.listings.models import Alert, District, Favorite, Listing, ListingMedia
from apps.listings.services import annonces
from apps.media import stockage, traitement
from apps.notifications.models import Notification

# (nom, slug, latitude, longitude)
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
    (
        "Chambre-salon à Banikanni",
        "chambre_salon",
        "banikanni",
        18000,
        True,
        True,
        450,
        "published",
        "#B8C7E0",
    ),
    (
        "Entrée-coucher à Guéma",
        "entree_coucher",
        "guema",
        12000,
        False,
        True,
        1200,
        "published",
        "#E4D2AE",
    ),
    (
        "Studio moderne près du campus",
        "studio",
        "titirou",
        35000,
        True,
        True,
        300,
        "published",
        "#C6D6C0",
    ),
    (
        "Chambre simple, quartier calme",
        "single",
        "zongo",
        15000,
        False,
        True,
        1500,
        "published",
        "#D9C3C3",
    ),
    (
        "Chambre avec cour et portail",
        "single",
        "albarika",
        20000,
        True,
        True,
        900,
        "published",
        "#C3CFD8",
    ),
    (
        "Studio avec eau courante",
        "studio",
        "madina",
        40000,
        True,
        False,
        2100,
        "rented",
        "#D2C6DE",
    ),
]

MOT_DE_PASSE_DEMO = "Passer1234!"


def _assombrir(teinte: str, facteur: float = 0.72) -> tuple[int, int, int]:
    """Renvoie une version assombrie d'une couleur hexadécimale `#RRGGBB`."""
    valeur = teinte.lstrip("#")
    r, v, b = (int(valeur[i : i + 2], 16) for i in (0, 2, 4))
    return (int(r * facteur), int(v * facteur), int(b * facteur))


def _generer_photo_demo(media: ListingMedia, teinte: str) -> None:
    """Écrit une photo de démonstration et ses variantes WebP, puis met à jour le média.

    Reproduit fidèlement ce que produit le pipeline d'envoi réel (`traitement.traiter_photo`)
    afin que les cartes affichent une vraie image servie sous /media/.
    """
    base = Image.new("RGB", (1600, 1000), teinte)
    dessin = ImageDraw.Draw(base)
    dessin.rectangle([0, 720, 1600, 1000], fill=_assombrir(teinte, 0.55))
    dessin.rectangle([140, 140, 640, 560], fill="#FFFFFF")
    dessin.rectangle([820, 520, 1460, 900], fill=_assombrir(teinte, 0.85))
    source = stockage.chemin_original(media.pk)
    base.save(source, "PNG")
    destination = stockage.dossier_public(media.listing_id, media.pk)
    meta = traitement.traiter_photo(source, destination)
    principale = meta["variants"][max(meta["variants"], key=int)]
    stockage.publier(media.listing_id, media.pk, destination)
    ListingMedia.objects.filter(pk=media.pk).update(
        status="ready",
        variants=meta["variants"],
        poster_path=stockage.cle(media.listing_id, media.pk, principale),
        mime_type=meta["mime"],
        width=meta["width"],
        height=meta["height"],
        size_bytes=source.stat().st_size,
        updated_at=timezone.now(),
    )
    media.refresh_from_db(fields=["poster_path", "variants"])


class Command(BaseCommand):
    help = "Crée les paramètres, les quartiers de Parakou et, avec --demo (développement), des données de démonstration complètes."

    def add_arguments(self, parser):
        parser.add_argument(
            "--demo",
            action="store_true",
            help="Ajoute les comptes, annonces, alertes et messages de démo.",
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
        # 1. Administrateur de démo
        admin, _ = User.objects.get_or_create(
            email="demo-admin@immoplus.test",
            defaults={
                "full_name": "Admin Immo+",
                "role": Role.ADMIN,
                "phone_e164": "+22901970000099",
            },
        )
        admin.set_password(MOT_DE_PASSE_DEMO)
        admin.save()

        # 2. Gérant vérifié de démo
        gerant, _ = User.objects.get_or_create(
            phone_e164="+22901970000001",
            defaults={
                "full_name": "Issa B.",
                "first_name": "Issa",
                "last_name": "B.",
                "role": Role.GERANT,
                "username": "issa.gerant",
            },
        )
        gerant.username = gerant.username or "issa.gerant"
        gerant.set_password(MOT_DE_PASSE_DEMO)
        gerant.save()

        profil_gerant = GerantProfile.complets.filter(pk=gerant.pk).first()
        if profil_gerant is None:
            profil_gerant = GerantProfile.complets.create(
                user=gerant, zone="Banikanni", created_by=admin
            )
        GerantProfile.complets.filter(pk=gerant.pk).update(
            verification_status=StatutVerification.VERIFIED, verified_at=timezone.now()
        )
        profil_gerant.refresh_from_db()

        # 3. Gérant en attente de validation (pour tester l'admin de modération)
        gerant_attente, _ = User.objects.get_or_create(
            phone_e164="+22901970000003",
            defaults={
                "full_name": "Koffi EnAttente",
                "first_name": "Koffi",
                "last_name": "EnAttente",
                "role": Role.GERANT,
                "username": "koffi.attente",
            },
        )
        gerant_attente.username = gerant_attente.username or "koffi.attente"
        gerant_attente.set_password(MOT_DE_PASSE_DEMO)
        gerant_attente.save()
        if not GerantProfile.complets.filter(pk=gerant_attente.pk).exists():
            GerantProfile.complets.create(user=gerant_attente, zone="Zongo", created_by=admin)

        # 4. Locataire étudiant de démo
        locataire, _ = User.objects.get_or_create(
            phone_e164="+22901970000002",
            defaults={
                "full_name": "Awa Étudiante",
                "first_name": "Awa",
                "last_name": "Étudiante",
                "role": Role.CLIENT,
                "username": "awa.etudiante",
            },
        )
        locataire.username = locataire.username or "awa.etudiante"
        locataire.set_password(MOT_DE_PASSE_DEMO)
        locataire.save()

        # 5. Annonces avec médias
        quartiers = {d.slug: d for d in District.objects.all()}
        annonces_creees = []
        for titre, type_, slug, loyer, douche, cloture, distance, statut, teinte in DEMO:
            district = quartiers[slug]
            annonce = Listing.objects.filter(title=titre, gerant=profil_gerant).first()
            if annonce is None:
                annonce = Listing(
                    gerant=profil_gerant,
                    title=titre,
                    room_type=type_,
                    district=district,
                    landmark_text=f"Près du marché de {district.name}",
                    address_private="Rue 14, quartier étudiant",
                    latitude=district.latitude,
                    longitude=district.longitude,
                    rent_amount=loyer,
                    deposit_months=2,
                    advance_months=1,
                    available_from=datetime.date.today() + datetime.timedelta(days=10),
                    has_private_bathroom=douche,
                    is_fenced=cloture,
                    water_sources=["running"],
                    electricity_meter="individual",
                    description_md=f"**{titre}**.\n\nChambre idéale pour étudiant(e) à Parakou.\n- Calme et sécurisée\n- Compteur individuel\n- Proche commodités",
                    description_html=f"<p><strong>{titre}</strong>.</p><p>Chambre idéale pour étudiant(e) à Parakou.</p><ul><li>Calme et sécurisée</li><li>Compteur individuel</li></ul>",
                    distance_to_campus_m=distance,
                    status=statut,
                    published_at=timezone.now(),
                    last_confirmed_at=timezone.now(),
                    slug=annonces._slug(titre),
                )
                annonce.save()
                annonces._vecteur_de_recherche(annonce)

                # Médias associés : photo de couverture et vidéo d'exemple.
                # La photo est générée localement (placeholder) et traitée par le même pipeline
                # que les vrais envois, afin de disposer des variantes WebP servies sous /media/.
                photo = ListingMedia.objects.create(
                    listing=annonce,
                    kind="photo",
                    position=0,
                    is_cover=True,
                    status="processing",
                    declared_size_bytes=240000,
                )
                _generer_photo_demo(photo, teinte)
                ListingMedia.objects.create(
                    listing=annonce,
                    kind="video",
                    position=1,
                    is_cover=False,
                    status="ready",
                    duration_s=18.5,
                    declared_size_bytes=1500000,
                    size_bytes=1500000,
                    playback_path=(
                        "https://commondatastorage.googleapis.com/"
                        "gtv-videos-bucket/sample/ForBiggerBlazes.mp4"
                    ),
                    poster_path=photo.poster_path,
                )
            annonces_creees.append(annonce)

        # 6. Favoris pour Awa
        if annonces_creees:
            Favorite.objects.get_or_create(user=locataire, listing=annonces_creees[0])
            if len(annonces_creees) > 2:
                Favorite.objects.get_or_create(user=locataire, listing=annonces_creees[2])

        # 7. Alertes actives pour Awa
        Alert.objects.get_or_create(
            user=locataire,
            label="Chambre Banikanni",
            defaults={
                "district_ids": [quartiers["banikanni"].id],
                "room_types": ["chambre_salon", "studio"],
                "max_rent": 20000,
                "private_bathroom_required": True,
                "is_active": True,
            },
        )
        Alert.objects.get_or_create(
            user=locataire,
            label="Entrée-coucher Guéma",
            defaults={
                "district_ids": [quartiers["guema"].id],
                "room_types": ["entree_coucher"],
                "max_rent": 15000,
                "private_bathroom_required": False,
                "is_active": True,
            },
        )

        # 8. Conversation réaliste entre Awa et Issa (fidèle à la maquette Conversation)
        if annonces_creees:
            premiere = annonces_creees[0]
            conv, _ = Conversation.objects.get_or_create(
                listing=premiere,
                client=locataire,
                defaults={
                    "gerant": gerant,
                    "status": "open",
                    "last_seq": 4,
                    "last_message_at": timezone.now(),
                    "last_sender": gerant,
                    "last_message_preview": "Exact, 2 mois. Je t'envoie le repère pour venir.",
                    "client_read_seq": 4,
                    "gerant_read_seq": 4,
                },
            )
            dialogue = [
                (1, locataire, "Bonjour, la chambre-salon à Banikanni est-elle toujours libre ?"),
                (2, gerant, "Oui, elle est libre. Tu peux passer la voir aujourd’hui après 15h."),
                (3, locataire, "D’accord. La caution c’est bien 2 mois ?"),
                (4, gerant, "Exact, 2 mois. Je t’envoie le repère pour venir."),
            ]
            for seq, auteur, texte in dialogue:
                Message.objects.get_or_create(
                    conversation=conv,
                    seq=seq,
                    defaults={
                        "sender": auteur,
                        "client_msg_id": uuid.uuid4(),
                        "body": texte,
                        "moderation_status": "visible",
                    },
                )

        # 9. Notifications de démo pour Awa (fidèles à la maquette Notifications)
        notifs_demo = [
            (
                "listing.alert_match",
                "Nouvelle entrée–coucher à Guéma",
                "Correspond à ton alerte · 12 000 F/mois",
                {"listing_slug": "entree-coucher-a-guema"},
                None,  # Non lue
            ),
            (
                "chat.message",
                "Issa B. t’a répondu",
                "À propos de la chambre–salon à Banikanni",
                {"conversation_id": str(conv.id) if annonces_creees else ""},
                None,  # Non lue
            ),
            (
                "listing.new_batch",
                "2 nouvelles chambres près de l’UP",
                "Découvre les dernières disponibilités à Titirou.",
                {},
                timezone.now() - datetime.timedelta(days=2),  # Lue
            ),
            (
                "listing.status_change",
                "Chambre louée à Titirou",
                "Celle que tu avais sauvegardée a trouvé preneur.",
                {},
                timezone.now() - datetime.timedelta(days=3),  # Lue
            ),
        ]
        for kind, titre, corps, data, lu_at in notifs_demo:
            dedupe = f"demo:{titre}"
            Notification.objects.get_or_create(
                dedupe_key=dedupe,
                defaults={
                    "user": locataire,
                    "kind": kind,
                    "title": titre,
                    "body": corps,
                    "data": data,
                    "read_at": lu_at,
                    "delivery_status": "sent",
                    "delivered_at": timezone.now(),
                },
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"""
========================================================================
🎉 Jeu de démonstration complet généré avec succès !
========================================================================

Identifiants de test (Mot de passe commun : {MOT_DE_PASSE_DEMO}) :
------------------------------------------------------------------------
1. Locataire (Awa) :
   - Numéro : +22901970000002
   - Données : 2 alertes, 2 favoris, 1 conversation active, 4 notifications.

2. Gérant vérifié (Issa) :
   - Numéro : +22901970000001
   - Données : Profil vérifié, 6 annonces (avec photos et vidéos), contacts reçus.

3. Gérant en attente (Koffi) :
   - Numéro : +22901970000003
   - Données : Profil non vérifié (idéal pour tester la modération admin).

4. Administrateur (Admin Immo+) :
   - Email  : demo-admin@immoplus.test (ou +22901970000099)
   - Accès  : http://pilotage.localhost:8080/ (ou port d'admin)
========================================================================
"""
            )
        )
