"""Messages entre l'équipe et les utilisateurs : questions, réponses, avis, décisions de modération."""

import pytest
from django.core import mail
from django.test import Client
from django.utils import timezone

from apps.accounts.tests.fabriques import (
    MOT_DE_PASSE,
    AdminFactory,
    ClientFactory,
    GerantFactory,
    PersonnelFactory,
)
from apps.core.errors import ErreurMetier
from apps.moderation import messages_equipe as equipe
from apps.moderation.models import MessageEquipe
from apps.notifications.models import Notification

pytestmark = [pytest.mark.pg, pytest.mark.django_db]


def test_l_equipe_ecrit_a_un_locataire(django_capture_on_commit_callbacks):
    locataire = ClientFactory(email="awa@exemple.bj", email_verified_at=timezone.now())
    modo = PersonnelFactory()
    with django_capture_on_commit_callbacks(execute=True):
        m = equipe.ecrire_a(
            modo, locataire, "Ton avis a été relu : il est conforme.\nMerci !", objet="À propos de ton avis"
        )
    assert m.vers_utilisateur and m.auteur_id == modo.pk and m.utilisateur_id == locataire.pk
    n = Notification.objects.get(user=locataire, kind="team.message")
    assert n.title == "À propos de ton avis" and n.data["url"] == "/compte/equipe"
    envoyes = [x for x in mail.outbox if "À propos de ton avis" in x.subject]
    assert [x.to for x in envoyes] == [["awa@exemple.bj"]]
    assert "Merci !" in envoyes[0].body and "/compte/equipe" in envoyes[0].body
    assert equipe.non_lus(locataire.pk) == 1
    equipe.marquer_lus(locataire.pk)
    assert equipe.non_lus(locataire.pk) == 0


def test_seul_le_personnel_ecrit_et_seulement_aux_utilisateurs():
    locataire = ClientFactory()
    with pytest.raises(ErreurMetier) as e:
        equipe.ecrire_a(ClientFactory(), locataire, "Bonjour")  # un locataire n'écrit pas « au nom de l'équipe »
    assert e.value.statut == 403
    with pytest.raises(ErreurMetier) as e:
        equipe.ecrire_a(AdminFactory(), PersonnelFactory(), "Bonjour")  # le personnel n'est pas un destinataire
    assert e.value.statut == 404
    with pytest.raises(ErreurMetier):
        equipe.ecrire_a(AdminFactory(), locataire, " ")  # message vide


def test_la_question_d_un_utilisateur_previent_l_equipe_puis_la_reponse_la_traite(
    django_capture_on_commit_callbacks,
):
    AdminFactory(email="admin@exemple.bj")
    gerant = GerantFactory(full_name="Koffi Gérant")
    with django_capture_on_commit_callbacks(execute=True):
        question = equipe.ecrire_a_l_equipe(gerant, "Comment payer mon abonnement ?")
    prevenus = [m for m in mail.outbox if "message de Koffi Gérant" in m.subject]
    assert [m.to for m in prevenus] == [["admin@exemple.bj"]]
    assert "/moderation/messageequipe/ecrire/" in prevenus[0].body
    assert question.traite_le is None
    equipe.ecrire_a(AdminFactory(), gerant, "Depuis la page Abonnement, avec KKiaPay.")
    question.refresh_from_db()
    assert question.traite_le is not None
    assert [m.vers_utilisateur for m in equipe.fil(gerant.pk)] == [False, True]


def test_cinq_questions_par_jour_au_plus():
    u = ClientFactory()
    for i in range(equipe.PAR_JOUR_MAX):
        equipe.ecrire_a_l_equipe(u, f"Question {i}")
    with pytest.raises(ErreurMetier) as e:
        equipe.ecrire_a_l_equipe(u, "Une de trop")
    assert e.value.statut == 429
    assert MessageEquipe.objects.filter(utilisateur=u).count() == equipe.PAR_JOUR_MAX


def test_la_page_equipe_du_site():
    u = ClientFactory(username="awa.test")
    equipe.ecrire_a(PersonnelFactory(), u, "Bienvenue sur Immo+.", objet="Bonjour")
    c = Client()
    assert Client().get("/compte/equipe").status_code == 302  # connexion obligatoire
    c.post("/connexion", {"username": "awa.test", "password": MOT_DE_PASSE})
    page = c.get("/compte/equipe").content.decode()
    assert "Bienvenue sur Immo+." in page and "L'équipe Immo+" in page
    assert equipe.non_lus(u.pk) == 0  # affiché : lu
    r = c.post("/compte/equipe", {"subject": "Aide", "body": "Je n'arrive pas à publier."})
    assert r.status_code == 302 and r["Location"] == "/compte/equipe?ok=envoye"
    assert MessageEquipe.objects.filter(utilisateur=u, vers_utilisateur=False).count() == 1
    assert "Je n'arrive pas à publier." in c.get("/compte/equipe").content.decode()
