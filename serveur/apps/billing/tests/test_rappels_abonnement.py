"""Rappels avant la fin d'un abonnement payant : 7 jours et 1 jour avant, une seule fois chacun."""

import datetime

import pytest
from django.core import mail
from django.utils import timezone

from apps.billing import services
from apps.billing.models import Subscription
from apps.core import parametres
from apps.listings.tests.fabriques import gerant_verifie
from apps.notifications.models import Notification

pytestmark = [pytest.mark.pg, pytest.mark.django_db]


@pytest.fixture(autouse=True)
def formules():
    parametres.definir("PLANS", [
        {"code": "free_v1", "label": "Gratuit", "price": 0, "period_months": 1, "active": True},
        {"code": "standard", "label": "Standard", "price": 500, "period_months": 1, "active": True},
    ])  # fmt: skip


def abonne(fin_dans_jours, *, annule=False):
    g = gerant_verifie()
    Subscription.objects.filter(gerant_id=g.pk).update(status="expired")
    maintenant = timezone.now()
    # Fin à midi (heure locale) : le nombre de jours restants ne dépend pas de l'heure à laquelle le test s'exécute.
    midi = timezone.localtime(maintenant).replace(hour=12, minute=0, second=0, microsecond=0)
    Subscription.objects.create(
        gerant_id=g.pk, plan_code="standard", status="active", cancel_at_period_end=annule,
        current_period_start=maintenant - datetime.timedelta(days=20),
        current_period_end=midi + datetime.timedelta(days=fin_dans_jours),
    )  # fmt: skip
    return g


def rappeler(capture):
    with capture(execute=True):
        return services.rappels_fin_abonnement()


def test_rappel_a_sept_jours_et_a_un_jour_seulement(django_capture_on_commit_callbacks):
    sept, un, trois, annule = abonne(7), abonne(1), abonne(3), abonne(7, annule=True)
    assert rappeler(django_capture_on_commit_callbacks) == {"rappels": 2}
    assert Notification.objects.filter(kind="subscription.reminder", user=sept.user).count() == 1
    assert Notification.objects.filter(kind="subscription.reminder", user=un.user).count() == 1
    assert not Notification.objects.filter(user__in=[trois.user, annule.user]).exists()


def test_un_seul_rappel_par_etape(django_capture_on_commit_callbacks):
    abonne(7)
    rappeler(django_capture_on_commit_callbacks)
    assert rappeler(django_capture_on_commit_callbacks) == {"rappels": 0}
    assert Notification.objects.filter(kind="subscription.reminder").count() == 1


def test_courriel_si_adresse_confirmee(django_capture_on_commit_callbacks):
    g = abonne(1)
    g.user.email, g.user.email_verified_at = "gerant@exemple.bj", timezone.now()
    g.user.save()
    rappeler(django_capture_on_commit_callbacks)
    envoyes = [m for m in mail.outbox if "se termine bientôt" in m.subject]
    assert [m.to for m in envoyes] == [["gerant@exemple.bj"]]
    assert "/compte/abonnement" in envoyes[0].body and "demain" in envoyes[0].body


def test_liste_vide_aucun_rappel(django_capture_on_commit_callbacks):
    abonne(7)
    parametres.definir("SUBSCRIPTION_REMINDER_DAYS", [])
    try:
        assert rappeler(django_capture_on_commit_callbacks) == {"rappels": 0}
    finally:
        parametres.definir("SUBSCRIPTION_REMINDER_DAYS", [7, 1])
