"""Déplace les photos et vidéos déjà en ligne vers Cloudinary ou vers le disque du serveur (ADR 0010).

python manage.py transferer_medias --vers cloudinary   # dans le conteneur worker
python manage.py transferer_medias --vers disque --limite 50
"""

from django.core.management.base import BaseCommand, CommandError

from apps.core.providers.stockage import CloudinaryStorageProvider
from apps.listings.services import rangement


class Command(BaseCommand):
    help = "Déplace les médias déjà en ligne entre le disque du serveur et Cloudinary."

    def add_arguments(self, parser):
        parser.add_argument("--vers", choices=["cloudinary", "disque"], required=True)
        parser.add_argument(
            "--limite", type=int, default=None, help="nombre maximum de médias (essai)"
        )

    def handle(self, *args, **options):
        if not CloudinaryStorageProvider.configure():
            raise CommandError("Cloudinary n'est pas configuré (CLOUDINARY_CLOUD_NAME absent).")
        if options["vers"] == "cloudinary":
            bilan = rangement.vers_cloudinary(options["limite"])
        else:
            bilan = rangement.vers_disque(options["limite"])
        self.stdout.write(
            f"Déplacés : {bilan['deplaces']} ; fichiers absents : {bilan['absents']} ; échecs : {bilan['echecs']}."
        )
        if bilan["echecs"]:
            raise CommandError(
                "Des médias n'ont pas été déplacés : relance la commande (journal pour le détail)."
            )
