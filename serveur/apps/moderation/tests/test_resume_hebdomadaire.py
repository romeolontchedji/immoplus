"""Résumé hebdomadaire à l'équipe : nouvelles annonces, signalements ouverts, paiements."""

import pytest
from django.core import mail
from django.utils import timezone

from apps.accounts.tests.fabriques import AdminFactory, PersonnelFactory
from apps.billing.models import Transaction
from apps.core import parametres
from apps.listings.tests.fabriques import ListingFactory
from apps.moderation import resume

pytestmark = [pytest.mark.pg, pytest.mark.django_db]


def test_le_resume_contient_les_trois_rubriques():
    annonce = ListingFactory(title="Chambre Zongo")
    admin = AdminFactory(email="equipe@exemple.bj")
    Transaction.objects.create(
        user=admin, objet="alerte", amount=150, status="succeeded", paid_at=timezone.now()
    )
    sujet, texte = resume.construire()
    assert "1 nouvelle(s) annonce(s)" in sujet
    assert "Nouvelles annonces : 1" in texte and annonce.title in texte
    assert "Signalements ouverts : 0" in texte
    assert "Paiements de la semaine : 1 pour 150 F (abonnements : 0, alertes : 1)" in texte
    assert "/statistiques/" in texte


def test_envoi_a_chaque_membre_de_l_equipe_et_parametre():
    AdminFactory(email="admin@exemple.bj")
    PersonnelFactory(email="modo@exemple.bj")
    assert resume.envoyer() == {"envoyes": 2}
    assert sorted(m.to[0] for m in mail.outbox if "résumé de la semaine" in m.subject) == [
        "admin@exemple.bj",
        "modo@exemple.bj",
    ]
    mail.outbox.clear()
    parametres.definir("EMAIL_RESUME_HEBDOMADAIRE", False)
    try:
        assert resume.envoyer() == {"envoyes": 0, "raison": "desactive"}
        assert not mail.outbox
    finally:
        parametres.definir("EMAIL_RESUME_HEBDOMADAIRE", True)
