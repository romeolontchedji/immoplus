"""Mise en forme des textes de notification (docs/design/COPYWRITING.md) : montants « 15 000 F », vrais pluriels,
titres courts. Un push Android coupe le titre vers 40 caractères : on tronque proprement plutôt que de le subir."""

ESPACE_FINE = " "


def francs(montant: int) -> str:
    """15000 → « 15 000 F » (espace fine insécable, comme sur le site)."""
    return f"{int(montant):,}".replace(",", ESPACE_FINE) + " F"


def pluriel(nombre: int, singulier: str, pluriel_: str | None = None) -> str:
    """« 1 jour », « 3 jours », « 2 messages non lus »."""
    return f"{nombre} {singulier if nombre <= 1 else (pluriel_ or singulier + 's')}"


def distance(metres: int | None) -> str | None:
    if metres is None:
        return None
    return f"{metres} m" if metres < 1000 else f"{metres / 1000:.1f} km".replace(".", ",")


def tronquer(texte: str, longueur: int) -> str:
    texte = " ".join((texte or "").split())
    return texte if len(texte) <= longueur else texte[: longueur - 1].rstrip() + "…"
