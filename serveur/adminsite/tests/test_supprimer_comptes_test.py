"""Commande de suppression définitive des comptes de test (ligne de commande, rôle propriétaire des tables)."""

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.accounts.models import User
from apps.accounts.tests.fabriques import AdminFactory, ClientFactory
from apps.audit import services as audit
from apps.audit.models import AuditLog
from apps.billing.models import Transaction
from apps.chat.models import Conversation
from apps.listings.models import Favorite, Listing
from apps.listings.tests.fabriques import ListingFactory, gerant_verifie

pytestmark = [pytest.mark.pg, pytest.mark.django_db(transaction=True)]


def lancer(*args):
    call_command("supprimer_comptes_test", *args, verbosity=0)


def test_simulation_ne_supprime_rien():
    u = ClientFactory(username="kofi.test")
    audit.enregistrer("compte.test", acteur=u)
    lancer("--nom-utilisateur", "kofi.test")
    assert User.objects.filter(pk=u.pk).exists()
    assert AuditLog.objects.filter(actor=u).exists()


def test_suppression_complete_d_un_locataire_et_de_ses_traces():
    annonce = ListingFactory()
    u = ClientFactory(username="kofi.test")
    Favorite.objects.create(user=u, listing=annonce)
    audit.enregistrer("compte.test", acteur=u)
    audit.enregistrer("compte.cible", cible=u)
    lancer("--nom-utilisateur", "kofi.test", "--confirmer", "SUPPRIMER")
    assert not User.objects.filter(pk=u.pk).exists()
    assert not Favorite.objects.filter(listing=annonce).exists()
    assert not AuditLog.objects.filter(actor_id=u.pk).exists()
    assert not AuditLog.objects.filter(target_id=str(u.pk)).exists()
    trace = AuditLog.objects.get(action="compte.supprime_definitivement")
    assert trace.metadata["id"] == str(u.pk) and "kofi" not in str(trace.metadata)
    assert Listing.objects.filter(pk=annonce.pk).exists()  # l'annonce d'un autre n'est pas touchée


def test_suppression_d_un_gerant_avec_ses_annonces_et_conversations():
    g = gerant_verifie()
    annonce = ListingFactory(gerant=g)
    locataire = ClientFactory()
    Conversation.objects.create(listing=annonce, client=locataire, gerant=g.user)
    audit.enregistrer("annonce.test", acteur=g.user)
    lancer("--id", str(g.user.pk), "--confirmer", "SUPPRIMER")
    assert not User.objects.filter(pk=g.user.pk).exists()
    assert not Listing.objects.filter(pk=annonce.pk).exists()
    assert not Conversation.objects.filter(listing_id=annonce.pk).exists()
    assert User.objects.filter(pk=locataire.pk).exists()  # l'autre côté de la conversation reste


def test_le_personnel_et_les_comptes_payes_sont_refuses():
    admin = AdminFactory()
    with pytest.raises(CommandError):
        lancer("--id", str(admin.pk), "--confirmer", "SUPPRIMER")
    u = ClientFactory(username="paye.test")
    Transaction.objects.create(user=u, objet="alerte", amount=150, status="succeeded")
    with pytest.raises(CommandError):
        lancer("--nom-utilisateur", "paye.test", "--confirmer", "SUPPRIMER")
    lancer("--nom-utilisateur", "paye.test", "--meme-payes", "--confirmer", "SUPPRIMER")
    assert not User.objects.filter(pk=u.pk).exists()


def test_les_restes_anonymises_se_nettoient():
    u = ClientFactory(username="supprime.abc123def456", status="deleted")
    ClientFactory(username="reste.actif")
    lancer("--anonymises", "--confirmer", "SUPPRIMER")
    assert not User.objects.filter(pk=u.pk).exists()
    assert User.objects.filter(username="reste.actif").exists()
