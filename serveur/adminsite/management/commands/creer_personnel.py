"""Crée un compte du personnel (modérateur ou administrateur). Jamais exposé par le web."""

import getpass

from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import ROLES_PERSONNEL, User
from apps.accounts.services import mots_de_passe
from apps.audit import services as audit
from apps.core.errors import ErreurMetier


class Command(BaseCommand):
    help = "Crée un compte du personnel (moderator ou admin)."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--nom", required=True)
        parser.add_argument("--role", choices=ROLES_PERSONNEL, default="moderator")
        parser.add_argument(
            "--mot-de-passe",
            help="À éviter : préférer la saisie interactive (historique du shell).",
        )

    def handle(self, *args, **options):
        if options["role"] not in ROLES_PERSONNEL:
            raise CommandError("Le rôle doit être moderator ou admin.")
        mdp = options["mot_de_passe"] or getpass.getpass("Mot de passe : ")
        try:
            mots_de_passe.valider(mdp)
        except ErreurMetier as erreur:
            raise CommandError(
                "; ".join(erreur.champs.get("password", [erreur.message]))
            ) from erreur
        email = options["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise CommandError("Un compte existe déjà avec cet e-mail.")
        utilisateur = User.objects.creer_personnel(
            email=email, password=mdp, full_name=options["nom"], role=options["role"]
        )
        audit.enregistrer(
            "admin.personnel_cree", cible=utilisateur, metadata={"role": utilisateur.role}
        )
        self.stdout.write(f"Compte créé : {utilisateur.email} ({utilisateur.role}).\n")
