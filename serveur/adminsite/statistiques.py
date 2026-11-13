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


# --------------------------------------------------------------------------- page « Statistiques » de l'administration
def vue_ensemble() -> dict:
    """Chiffres clés de la plateforme, puis le détail par gérant et par locataire (100 premiers, les plus actifs)."""
    import datetime

    from django.utils import timezone

    from apps.accounts.models import GerantProfile, User

    il_y_a_30j = timezone.now() - datetime.timedelta(days=30)
    comptes_actifs = User.objects.filter(status="active", deleted_at__isnull=True)
    ventes = Transaction.objects.filter(status="succeeded")
    payants = Subscription.objects.filter(status__in=["active", "past_due", "trialing"]).exclude(
        plan_code="free_v1"
    )
    globaux = [
        ("Gérants actifs", comptes_actifs.filter(role="gerant").count()),
        (
            "Gérants vérifiés",
            GerantProfile.objects.filter(
                verification_status="verified", user__deleted_at__isnull=True
            ).count(),
        ),
        ("Locataires actifs", comptes_actifs.filter(role="client").count()),
        ("Nouveaux comptes (30 jours)", User.objects.filter(created_at__gte=il_y_a_30j).count()),
        ("Annonces en ligne", Listing.objects.filter(status="published", deleted_at__isnull=True).count()),
        (
            "Chambres louées",
            Listing.objects.filter(rented_at__isnull=False).count(),
        ),
        ("Conversations (30 jours)", Conversation.objects.filter(created_at__gte=il_y_a_30j).count()),
        ("Alertes actives", Alert.objects.filter(is_active=True).count()),
        ("Abonnements payants en cours", payants.count()),
        ("Paiements réussis", ventes.count()),
        ("Total encaissé", f"{ventes.aggregate(t=Sum('amount'))['t'] or 0} F"),
        (
            "Encaissé (30 jours)",
            f"{ventes.filter(paid_at__gte=il_y_a_30j).aggregate(t=Sum('amount'))['t'] or 0} F",
        ),
    ]

    # --- par gérant (quelques requêtes groupées, jamais une par ligne)
    profils = list(
        GerantProfile.objects.select_related("user").filter(user__deleted_at__isnull=True)
    )
    en_ligne = dict(
        Listing.objects.filter(status="published", deleted_at__isnull=True)
        .values_list("gerant_id")
        .annotate(n=Count("id"))
        .values_list("gerant_id", "n")
    )
    totaux = dict(
        Listing.objects.filter(deleted_at__isnull=True)
        .values_list("gerant_id")
        .annotate(n=Count("id"))
        .values_list("gerant_id", "n")
    )
    echanges = dict(
        Conversation.objects.values_list("gerant_id").annotate(n=Count("id")).values_list("gerant_id", "n")
    )
    notes = {
        ligne["gerant_id"]: (ligne["moyenne"], ligne["n"])
        for ligne in Review.objects.filter(is_hidden=False, gerant__isnull=False)
        .values("gerant_id")
        .annotate(moyenne=Avg("rating"), n=Count("id"))
    }
    formules = {p["code"]: p["label"] for p in parametres.lire("PLANS")}
    abonnements = {
        s.gerant_id: s
        for s in Subscription.objects.exclude(status="expired").order_by("created_at")
    }
    gerants = []
    for p in profils:
        note = notes.get(p.pk)
        abo = abonnements.get(p.pk)
        gerants.append(
            {
                "id": p.user_id,
                "nom": p.display_name or p.user.full_name,
                "zone": p.zone,
                "verifie": p.verification_status == "verified",
                "en_ligne": en_ligne.get(p.pk, 0),
                "total": totaux.get(p.pk, 0),
                "conversations": echanges.get(p.user_id, 0),
                "note": round(note[0], 1) if note else None,
                "avis": note[1] if note else 0,
                "formule": formules.get(abo.plan_code, abo.plan_code) if abo else "—",
                "fin": _date(abo.current_period_end) if abo and abo.plan_code != "free_v1" else "—",
            }
        )
    gerants.sort(key=lambda g: (-g["en_ligne"], -g["conversations"]))

    # --- par locataire
    clients = list(
        User.objects.filter(role="client", deleted_at__isnull=True).order_by("-last_seen_at", "-created_at")[:100]
    )
    ids = [c.pk for c in clients]
    conv = dict(
        Conversation.objects.filter(client_id__in=ids).values_list("client_id").annotate(n=Count("id")).values_list("client_id", "n")
    )
    favs = dict(
        Favorite.objects.filter(user_id__in=ids).values_list("user_id").annotate(n=Count("id")).values_list("user_id", "n")
    )
    alertes = dict(
        Alert.objects.filter(user_id__in=ids, is_active=True).values_list("user_id").annotate(n=Count("id")).values_list("user_id", "n")
    )
    payes = dict(
        ventes.filter(user_id__in=ids).values_list("user_id").annotate(t=Sum("amount")).values_list("user_id", "t")
    )
    locataires = [
        {
            "id": c.pk,
            "nom": c.full_name or c.username,
            "inscrit": _date(c.created_at),
            "vu": _date(c.last_seen_at),
            "conversations": conv.get(c.pk, 0),
            "favoris": favs.get(c.pk, 0),
            "alertes": alertes.get(c.pk, 0),
            "paye": payes.get(c.pk, 0),
        }
        for c in clients
    ]
    return {"globaux": globaux, "gerants": gerants[:100], "locataires": locataires}
