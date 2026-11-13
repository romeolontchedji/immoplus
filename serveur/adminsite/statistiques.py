"""Statistiques d'un gérant ou d'un locataire, pour sa fiche dans l'administration (lecture seule)."""

import logging

from django.db.models import Avg, Count, Sum
from django.utils.html import format_html, format_html_join

from apps.accounts import selectors as comptes
from apps.billing.models import Subscription, Transaction
from apps.chat.models import Conversation
from apps.core import parametres
from apps.listings import selectors as annonces
from apps.listings.models import Alert, Favorite, Listing, Review

journal = logging.getLogger(__name__)


def _date(valeur) -> str:
    return valeur.strftime("%d/%m/%Y") if valeur else "—"


def _paiements(utilisateur) -> list[tuple[str, object]]:
    reussis = Transaction.objects.filter(user=utilisateur, status="succeeded")
    somme = reussis.aggregate(total=Sum("amount"), n=Count("id"))
    return [
        ("Paiements réussis", somme["n"] or 0),
        ("Total payé", f"{somme['total'] or 0} F"),
    ]


def _gerant(utilisateur) -> list[tuple[str, list[tuple[str, object]]]]:
    profil = comptes.profil_gerant_par_id(utilisateur.pk)
    if profil is None:
        return []
    base = Listing.objects.filter(gerant_id=profil.pk, deleted_at__isnull=True)
    statuts = dict(base.values_list("status").annotate(n=Count("id")).values_list("status", "n"))
    louees = base.filter(status="archived", rented_at__isnull=False).count() + statuts.get(
        "rented", 0
    )
    try:
        tableau = annonces.tableau_de_bord_gerant(profil)
    except Exception:  # noqa: BLE001 - compteurs de vues indisponibles : le reste s'affiche
        journal.exception("statistiques_vues_indisponibles")
        tableau = {"views_30d": "—", "views_total": "—", "favorites_30d": "—", "conversations_30d": "—"}
    avis = annonces.resume_avis_gerant(profil.pk)
    conversations = Conversation.objects.filter(gerant_id=utilisateur.pk)
    courant = Subscription.objects.filter(gerant_id=profil.pk).exclude(status="expired").first()
    formules = {p["code"]: p["label"] for p in parametres.lire("PLANS")}
    return [
        (
            "Annonces",
            [
                ("En ligne", statuts.get("published", 0)),
                ("Brouillons", statuts.get("draft", 0)),
                ("En attente de traitement", statuts.get("processing", 0)),
                ("Masquées", statuts.get("hidden", 0)),
                ("Louées (archivées)", louees),
                ("Au total", base.count()),
            ],
        ),
        (
            "Audience",
            [
                ("Vues (30 jours)", tableau["views_30d"]),
                ("Vues (depuis le début)", tableau["views_total"]),
                ("Favoris ajoutés (30 jours)", tableau["favorites_30d"]),
                ("Conversations ouvertes (30 jours)", tableau["conversations_30d"]),
                ("Conversations (au total)", conversations.count()),
                (
                    "Taux de réponse (30 jours)",
                    f"{profil.response_rate_30d} %" if profil.response_rate_30d is not None else "—",
                ),
                (
                    "Délai de réponse médian",
                    f"{profil.median_response_min} min" if profil.median_response_min else "—",
                ),
            ],
        ),
        (
            "Réputation",
            [
                ("Note moyenne", avis["average"] if avis["average"] is not None else "—"),
                ("Nombre d'avis", avis["count"]),
            ],
        ),
        (
            "Abonnement et paiements",
            [
                (
                    "Formule",
                    f"{formules.get(courant.plan_code, courant.plan_code)} ({courant.get_status_display()})"
                    if courant
                    else "Aucune",
                ),
                ("Valable jusqu'au", _date(courant.current_period_end) if courant else "—"),
                *_paiements(utilisateur),
            ],
        ),
    ]


def _client(utilisateur) -> list[tuple[str, list[tuple[str, object]]]]:
    conversations = Conversation.objects.filter(client_id=utilisateur.pk)
    alertes = Alert.objects.filter(user=utilisateur)
    avis = Review.objects.filter(author=utilisateur).aggregate(n=Count("id"), moyenne=Avg("rating"))
    return [
        (
            "Activité",
            [
                ("Conversations", conversations.count()),
                ("Favoris", Favorite.objects.filter(user=utilisateur).count()),
                ("Alertes actives", alertes.filter(is_active=True).count()),
                ("Alertes (au total)", alertes.count()),
                ("Avis donnés", avis["n"]),
                ("Note moyenne donnée", round(avis["moyenne"], 1) if avis["moyenne"] else "—"),
            ],
        ),
        (
            "Paiements",
            [
                *_paiements(utilisateur),
                (
                    "Alertes payées non créées",
                    Transaction.objects.filter(
                        user=utilisateur, objet="alerte", status="succeeded", used_at__isnull=True
                    ).count(),
                ),
            ],
        ),
    ]


def statistiques_html(utilisateur):
    """Tableau HTML des statistiques ; une défaillance d'une lecture n'empêche jamais d'ouvrir la fiche."""
    if utilisateur is None or utilisateur.role not in ("gerant", "client"):
        return "—"
    try:
        sections = _gerant(utilisateur) if utilisateur.role == "gerant" else _client(utilisateur)
    except Exception:  # noqa: BLE001 - l'administration reste utilisable
        journal.exception("statistiques_indisponibles")
        return "Statistiques indisponibles pour le moment."
    blocs = format_html_join(
        "",
        '<div style="margin:0 0 14px"><strong>{}</strong><table style="margin-top:4px">{}</table></div>',
        (
            (
                titre,
                format_html_join("", "<tr><td>{}</td><td><strong>{}</strong></td></tr>", lignes),
            )
            for titre, lignes in sections
        ),
    )
    return format_html("<div>{}</div>", blocs)
