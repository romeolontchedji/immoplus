"""Courriels : texte brut conservé, version HTML aux couleurs d'Immo+."""

from django.core import mail

from apps.core.tasks import courriel_html, envoyer_courriel


def test_le_html_met_le_lien_en_bouton_et_echappe_le_texte():
    html = courriel_html(
        "Sujet <b>", "Titre : Chambre <script>\nVoir l'annonce : https://exemple.bj/a/1"
    )
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert 'href="https://exemple.bj/a/1"' in html and "background:#1B44D6" in html


def test_un_courriel_part_en_texte_et_en_html():
    envoyer_courriel(["a@exemple.bj"], "Bonjour", "Ligne un\nhttps://exemple.bj")
    message = mail.outbox[-1]
    assert message.body.startswith("Ligne un")
    assert message.alternatives[0][1] == "text/html"
