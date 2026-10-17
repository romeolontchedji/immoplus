from django.apps import AppConfig


class ListingsConfig(AppConfig):
    name = "apps.listings"
    label = "listings"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        from apps.core import configuration

        from . import receivers  # noqa: F401  (comptes suspendus, bannis, supprimés)
        from .enums import TypeMedia
        from .services import favoris, filtres, medias

        configuration.declarer_limites(
            favorites_max=favoris.LIMITE,
            photos_max=medias.PHOTOS_MAX,
            photo_max_bytes=medias.TAILLE_MAX[TypeMedia.PHOTO],
            video_max_bytes=medias.TAILLE_MAX[TypeMedia.VIDEO],
            upload_chunk_max_bytes=medias.MORCEAU_MAX,
            page_size_default=filtres.LIMITE_DEFAUT,
            page_size_max=filtres.LIMITE_MAX,
        )
