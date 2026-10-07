import pytest

from apps.accounts.models import Device
from apps.accounts.services import appareils, jetons
from apps.accounts.tests.fabriques import ClientFactory
from apps.core.errors import ErreurMetier

pytestmark = [pytest.mark.integration, pytest.mark.pg, pytest.mark.django_db]


def ouvrir(u, installation="inst-1", **kw):
    return appareils.ouvrir(u, installation_id=installation, platform="android", **kw)


def test_ouverture_cree_un_appareil():
    u = ClientFactory()
    d, refresh = ouvrir(u, app_version="1.2.0", label="Tecno Spark", ip="41.0.0.1")
    assert (d.label, d.app_version, d.last_ip) == ("Tecno Spark", "1.2.0", "41.0.0.1")
    assert d.refresh_hash == jetons.empreinte(refresh)


def test_une_meme_installation_reutilise_la_meme_ligne():
    u = ClientFactory()
    d1, r1 = ouvrir(u)
    d2, r2 = ouvrir(u)
    assert d1.pk == d2.pk and r1 != r2 and Device.objects.filter(user=u).count() == 1


def test_une_installation_revoquee_se_reconnecte():
    u = ClientFactory()
    d, _ = ouvrir(u)
    jetons.revoquer_appareil(d)
    d2, _ = ouvrir(u)
    d2.refresh_from_db()
    assert d2.revoked_at is None
    acces = jetons.emettre_acces(u, d2)
    jetons.verifier_acces(acces)


def test_plateforme_inconnue_refusee():
    with pytest.raises(ErreurMetier):
        appareils.ouvrir(ClientFactory(), installation_id="i", platform="symbian")


def test_liste_limitee_aux_appareils_actifs_du_compte():
    u, autre = ClientFactory(), ClientFactory()
    d1, _ = ouvrir(u, "a")
    d2, _ = ouvrir(u, "b")
    ouvrir(autre, "c")
    jetons.revoquer_appareil(d2)
    assert [d.pk for d in appareils.lister(u)] == [d1.pk]


def test_revoquer_son_appareil():
    u = ClientFactory()
    d, _ = ouvrir(u)
    appareils.revoquer(u, d.pk)
    assert appareils.lister(u) == []


def test_impossible_de_revoquer_l_appareil_d_autrui():
    pirate, victime = ClientFactory(), ClientFactory()
    d, _ = ouvrir(victime)
    with pytest.raises(ErreurMetier) as e:
        appareils.revoquer(pirate, d.pk)
    assert e.value.statut == 404  # on ne distingue pas « n'existe pas » de « pas à toi »
    assert len(appareils.lister(victime)) == 1


@pytest.mark.parametrize("mauvais", ["pas-un-uuid", None, "00000000-0000-0000-0000-000000000000"])
def test_identifiant_d_appareil_invalide(mauvais):
    with pytest.raises(ErreurMetier) as e:
        appareils.revoquer(ClientFactory(), mauvais)
    assert e.value.statut == 404


def test_revoquer_les_autres_garde_l_appareil_courant():
    u = ClientFactory()
    courant, _ = ouvrir(u, "a")
    ouvrir(u, "b")
    ouvrir(u, "c")
    assert appareils.revoquer_autres(u, courant.pk) == 2
    assert [d.pk for d in appareils.lister(u)] == [courant.pk]


def test_revoquer_tous():
    u = ClientFactory()
    ouvrir(u, "a")
    ouvrir(u, "b")
    assert appareils.revoquer_autres(u, None) == 2
    assert appareils.lister(u) == []


def test_jeton_de_notification():
    d, _ = ouvrir(ClientFactory())
    appareils.enregistrer_push(d, "expo", "ExponentPushToken[abc]")
    d.refresh_from_db()
    assert (d.push_provider, d.push_token) == ("expo", "ExponentPushToken[abc]")


@pytest.mark.parametrize(
    ("fournisseur", "jeton"), [("pigeon", "x"), ("expo", ""), ("expo", "x" * 5000)]
)
def test_jeton_de_notification_invalide(fournisseur, jeton):
    d, _ = ouvrir(ClientFactory())
    with pytest.raises(ErreurMetier):
        appareils.enregistrer_push(d, fournisseur, jeton)


def test_la_revocation_efface_le_jeton_de_notification():
    d, _ = ouvrir(ClientFactory())
    appareils.enregistrer_push(d, "fcm", "tok")
    jetons.revoquer_appareil(d)
    d.refresh_from_db()
    assert d.push_token is None
