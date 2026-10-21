"""Courriels en développement : rangés dans la « boîte de développement » au lieu d'être envoyés.

Les journaux masquent les codes à 6 chiffres (confidentialité) : en développement, on lit donc les courriels sur
http://www.localhost:8080/dev/boite (avec les SMS et les push), ou dans `docker compose logs worker`.
Jamais utilisé en production (réglage EMAIL_BACKEND de settings/local.py seulement).
"""

import sys

from django.core.cache import cache
from django.core.mail.backends.base import BaseEmailBackend as MoteurCourriel
from django.utils import timezone

CLE_BOITE_COURRIELS = "dev:boite-courriels"


class BoiteDevCourriels(MoteurCourriel):
    def send_messages(self, messages) -> int:
        boite = cache.get(CLE_BOITE_COURRIELS, [])
        for m in messages:
            boite.insert(
                0,
                {
                    "a": ", ".join(m.to),
                    "sujet": m.subject,
                    "texte": m.body,
                    "quand": timezone.localtime().strftime("%H:%M:%S"),
                },
            )
            sys.stderr.write(f"[courriel dev] à {', '.join(m.to)} : {m.subject}\n")
        cache.set(CLE_BOITE_COURRIELS, boite[:50], 3600)
        return len(messages)
