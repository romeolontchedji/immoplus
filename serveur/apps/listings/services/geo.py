"""Distance au campus (haversine) et arrondis d'affichage (CDC §11.6)."""

import math
from decimal import Decimal

from apps.core import parametres

RAYON_TERRE_M = 6_371_000


def haversine_m(lat1, lon1, lat2, lon2) -> int:
    p1, p2 = math.radians(float(lat1)), math.radians(float(lat2))
    dp, dl = p2 - p1, math.radians(float(lon2) - float(lon1))
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(2 * RAYON_TERRE_M * math.asin(math.sqrt(a)))


def distance_au_campus(latitude, longitude) -> int:
    ref = parametres.lire("CAMPUS_REFERENCE")
    return haversine_m(latitude, longitude, ref["latitude"], ref["longitude"])


def arrondir_50(metres: int) -> int:
    return int(round(metres / 50) * 50)


def arrondir_position(valeur) -> float:
    """Position publique : 3 décimales (environ 110 m)."""
    return float(round(Decimal(str(valeur)), 3))
