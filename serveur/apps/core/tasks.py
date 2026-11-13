"""Tâches transverses : envoi d'un courriel (codes de l'administration, alertes d'erreurs).

L'envoi part du `worker` (réseau `sortie`) : l'administration n'a volontairement pas accès à Internet, elle dépose la
demande dans la file et n'envoie jamais elle-même.
"""

import re
from html import escape

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives

BLEU = "#1B44D6"  # couleurs du site (web/static/css/tokens.css)
BLEU_PALE = "#EAF0FF"
ENCRE = "#0F1B3D"
GRIS = "#5B6478"
LIEN = re.compile(r"https?://\S+")
# « Libellé : https://… » seul sur sa ligne : bouton d'action
LIGNE_ACTION = re.compile(r"^(?P<libelle>[^:]{2,40}) : (?P<url>https?://\S+)$")


def _ligne_html(ligne: str) -> str:
    action = LIGNE_ACTION.match(ligne)
    if action:
        return (
            f'<p style="margin:18px 0 6px"><a href="{escape(action["url"], quote=True)}" '
            f'style="display:inline-block;background:{BLEU};color:#ffffff;text-decoration:none;'
            f'font-weight:600;padding:11px 20px;border-radius:10px">{escape(action["libelle"])}</a></p>'
        )
    if not ligne.strip():
        return ""
    corps = escape(ligne)
    corps = LIEN.sub(
        lambda m: f'<a href="{m.group(0)}" style="color:{BLEU}">{m.group(0)}</a>', corps
    )
    if re.match(r"^[^:]{2,30} : ", ligne):  # « Titre : valeur » : libellé en retrait discret
        libelle, _, valeur = corps.partition(" : ")
        corps = f'<span style="color:{GRIS}">{libelle}</span> · <strong>{valeur}</strong>'
    return f'<p style="margin:6px 0;line-height:1.55">{corps}</p>'


def courriel_html(sujet: str, texte: str) -> str:
    """Version HTML d'un courriel texte : bandeau bleu Immo+, corps lisible, liens cliquables."""
    corps = "".join(_ligne_html(ligne) for ligne in texte.splitlines())
    return (
        f'<!doctype html><html lang="fr"><body style="margin:0;background:{BLEU_PALE};'
        'font-family:Helvetica,Arial,sans-serif">'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>'
        '<td align="center" style="padding:24px 12px">'
        f'<table role="presentation" width="560" cellpadding="0" cellspacing="0" style="max-width:560px;'
        'background:#ffffff;border-radius:14px;overflow:hidden">'
        f'<tr><td style="background:{BLEU};color:#ffffff;padding:18px 24px;font-size:22px;'
        'font-weight:700">Immo+</td></tr>'
        f'<tr><td style="padding:24px;color:{ENCRE};font-size:15px">'
        f'<h1 style="margin:0 0 14px;font-size:18px;color:{ENCRE}">{escape(sujet)}</h1>{corps}</td></tr>'
        f'<tr><td style="padding:14px 24px;background:#F6F8FD;color:{GRIS};font-size:12px">'
        "Immo+ · trouver une chambre au Bénin, sans intermédiaire inutile.</td></tr>"
        "</table></td></tr></table></body></html>"
    )


# Le nom commence par `apps.notifications.` : même file que les push, traitée en priorité (config.celery).
@shared_task(
    name="apps.notifications.envoyer_courriel",
    autoretry_for=(OSError,),
    retry_backoff=10,
    retry_kwargs={"max_retries": 4},
)
def envoyer_courriel(destinataires: list[str], sujet: str, texte: str) -> int:
    """Envoie un courriel (texte + version HTML habillée). Reprises en cas de panne réseau ou SMTP (4 essais)."""
    message = EmailMultiAlternatives(sujet, texte, settings.DEFAULT_FROM_EMAIL, destinataires)
    message.attach_alternative(courriel_html(sujet, texte), "text/html")
    return message.send(fail_silently=False)
