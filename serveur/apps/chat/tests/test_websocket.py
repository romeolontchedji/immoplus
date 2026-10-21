"""WebSocket : ticket, plafond de connexions, présence, événements, limites de trames (CDC §10.8)."""

import asyncio
import datetime
import json
import uuid

import pytest

pytest.importorskip("daphne", reason="channels.testing exige daphne (voir docs/a-verifier.md)")

from asgiref.sync import sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.utils import timezone

from apps.accounts.tests.fabriques import ClientFactory
from apps.chat import consumers, services, ws
from apps.chat.routing import websocket_urlpatterns
from apps.core import presence
from apps.listings.tests.fabriques import ListingFactory, gerant_verifie

pytestmark = [pytest.mark.integration, pytest.mark.pg, pytest.mark.django_db(transaction=True)]

application = URLRouter(websocket_urlpatterns)


async def connecter(utilisateur, appareil="appareil-1", ticket=None):
    ticket = ticket or await sync_to_async(ws.emettre)(utilisateur.pk, appareil)
    communicator = WebsocketCommunicator(application, f"/ws/v1/?ticket={ticket}")
    connecte, code = await communicator.connect()
    return communicator, connecte, code


async def lire_json(communicator, delai=2):
    return json.loads(await communicator.receive_from(timeout=delai))


@pytest.fixture
def decor():
    gerant = gerant_verifie()
    return type(
        "D",
        (),
        {"gerant": gerant, "annonce": ListingFactory(gerant=gerant), "locataire": ClientFactory()},
    )


async def test_ticket_invalide_ou_absent_ferme_en_4401():
    for ticket in ("n-importe-quoi", ""):
        communicator = WebsocketCommunicator(application, f"/ws/v1/?ticket={ticket}")
        connecte, code = await communicator.connect()
        assert not connecte and code == 4401


async def test_ticket_a_usage_unique():
    utilisateur = await sync_to_async(ClientFactory)()
    ticket = await sync_to_async(ws.emettre)(utilisateur.pk, "a1")
    c1, connecte, _ = await connecter(utilisateur, ticket=ticket)
    assert connecte
    _, rejoue, code = await connecter(utilisateur, ticket=ticket)
    assert not rejoue and code == 4401
    await c1.disconnect()


async def test_compte_suspendu_refuse_en_4403():
    utilisateur = await sync_to_async(ClientFactory)(
        status="suspended", suspended_until=timezone.now() + datetime.timedelta(days=2)
    )
    _, connecte, code = await connecter(utilisateur)
    assert not connecte and code == 4403


async def test_ping_pong_et_presence_de_conversation(decor):
    conversation, *_ = await sync_to_async(services.ouvrir)(
        decor.locataire, decor.annonce.pk, "Bonjour", str(uuid.uuid4())
    )
    c, connecte, _ = await connecter(decor.locataire, "appareil-9")
    assert connecte
    await c.send_json_to({"type": "ping"})
    assert (await lire_json(c))["type"] == "pong"
    await c.send_json_to(
        {"type": "conversation.focus", "data": {"conversation_id": str(conversation.pk)}}
    )
    await asyncio.sleep(0.2)
    assert await sync_to_async(presence.appareils_sur_conversation)(
        decor.locataire.pk, conversation.pk
    ) == {"appareil-9"}
    await c.send_json_to({"type": "conversation.focus", "data": {"conversation_id": None}})
    await asyncio.sleep(0.2)
    assert (
        await sync_to_async(presence.appareils_sur_conversation)(
            decor.locataire.pk, conversation.pk
        )
        == set()
    )
    await c.send_json_to(
        {"type": "conversation.focus", "data": {"conversation_id": str(conversation.pk)}}
    )
    await asyncio.sleep(0.2)
    await c.disconnect()
    await asyncio.sleep(0.2)
    assert (
        await sync_to_async(presence.appareils_sur_conversation)(
            decor.locataire.pk, conversation.pk
        )
        == set()
    )


async def test_focus_sur_une_conversation_etrangere_ne_pose_rien(decor):
    conversation, *_ = await sync_to_async(services.ouvrir)(
        decor.locataire, decor.annonce.pk, "Bonjour", str(uuid.uuid4())
    )
    intrus = await sync_to_async(ClientFactory)()
    c, _, _ = await connecter(intrus, "appareil-x")
    await c.send_json_to(
        {"type": "conversation.focus", "data": {"conversation_id": str(conversation.pk)}}
    )
    await asyncio.sleep(0.2)
    assert (
        await sync_to_async(presence.appareils_sur_conversation)(intrus.pk, conversation.pk)
        == set()
    )
    await c.disconnect()


async def test_message_diffuse_aux_deux_participants_avec_le_bon_texte(decor):
    conversation, *_ = await sync_to_async(services.ouvrir)(
        decor.locataire, decor.annonce.pk, "Bonjour", str(uuid.uuid4())
    )
    loc, _, _ = await connecter(decor.locataire, "a-loc")
    ger, _, _ = await connecter(decor.gerant.user, "a-ger")
    await sync_to_async(services.envoyer)(
        decor.locataire, conversation.pk, "Mon numéro 97 12 34 56", str(uuid.uuid4())
    )
    chez_ger = await lire_json(ger)
    chez_loc = await lire_json(loc)
    assert chez_ger["type"] == chez_loc["type"] == "message.new"
    assert (
        "97 12" not in chez_ger["data"]["message"]["body"]
        and "97 12" in chez_loc["data"]["message"]["body"]
    )
    assert chez_ger["data"]["message"]["seq"] == 2
    await sync_to_async(services.lire)(decor.gerant.user, conversation.pk, 2)
    accuse = await lire_json(loc)
    # d'autres événements (notification) peuvent s'intercaler : on cherche l'accusé
    while accuse["type"] != "conversation.read":
        accuse = await lire_json(loc)
    assert accuse["data"]["up_to_seq"] == 2
    await loc.disconnect()
    await ger.disconnect()


async def test_notification_diffusee_avec_le_compteur(decor):
    from apps.notifications import services as notifications

    c, _, _ = await connecter(decor.locataire)
    await sync_to_async(notifications.creer)(decor.locataire.pk, "alert.match", "Titre", "Corps")
    evenement = await lire_json(c)
    assert evenement["type"] == "notification.new" and evenement["data"]["unread_count"] == 1
    await c.disconnect()


async def test_cinq_connexions_au_plus_par_utilisateur():
    utilisateur = await sync_to_async(ClientFactory)()
    ouvertes = []
    for i in range(5):
        c, connecte, _ = await connecter(utilisateur, f"a{i}")
        assert connecte
        ouvertes.append(c)
    _, sixieme, code = await connecter(utilisateur, "a6")
    assert not sixieme and code == 4429
    await ouvertes[0].disconnect()
    await asyncio.sleep(0.2)
    c7, septieme, _ = await connecter(utilisateur, "a7")
    assert septieme
    for c in [*ouvertes[1:], c7]:
        await c.disconnect()


async def test_trame_trop_grosse_et_trames_invalides():
    utilisateur = await sync_to_async(ClientFactory)()
    c, _, _ = await connecter(utilisateur)
    await c.send_to(text_data="pas du json")
    assert (await lire_json(c))["data"]["code"] == "bad_frame"
    await c.send_json_to({"type": "inconnu"})
    assert (await lire_json(c))["data"]["code"] == "unknown_event"
    await c.send_to(text_data=json.dumps({"type": "ping", "data": {"x": "a" * 9000}}))
    sortie = await c.receive_output(timeout=2)
    assert sortie["type"] == "websocket.close" and sortie["code"] == 1009


async def test_plus_de_trente_evenements_par_minute():
    utilisateur = await sync_to_async(ClientFactory)()
    c, _, _ = await connecter(utilisateur)
    for _ in range(consumers.EVENEMENTS_PAR_MINUTE):
        await c.send_json_to({"type": "ping"})
        await lire_json(c)
    await c.send_json_to({"type": "ping"})
    assert (await lire_json(c))["data"]["code"] == 4429
    assert (await c.receive_output(timeout=2))["code"] == 4429


async def test_fermeture_apres_inactivite(monkeypatch):
    monkeypatch.setattr(consumers.MessagerieConsumer, "inactivite_s", 0.6)
    utilisateur = await sync_to_async(ClientFactory)()
    c, _, _ = await connecter(utilisateur)
    sortie = await c.receive_output(timeout=3)
    assert sortie["type"] == "websocket.close" and sortie["code"] == 4408


async def test_un_ping_regulier_garde_la_connexion(monkeypatch):
    monkeypatch.setattr(consumers.MessagerieConsumer, "inactivite_s", 0.8)
    utilisateur = await sync_to_async(ClientFactory)()
    c, _, _ = await connecter(utilisateur)
    for _ in range(4):
        await asyncio.sleep(0.3)
        await c.send_json_to({"type": "ping"})
        assert (await lire_json(c))["type"] == "pong"
    await c.disconnect()
