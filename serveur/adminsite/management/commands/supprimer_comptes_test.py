"""Supprime DÉFINITIVEMENT des comptes de test (ligne de commande seulement, jamais depuis le web).

Pourquoi une commande à part : un compte ne se supprime normalement jamais (il est anonymisé), car le journal d'activité,
les messages et les annonces gardent leurs liens et que le journal est protégé contre toute modification dans la base.
Pour effacer des comptes créés pour des essais, cette commande, lancée avec le rôle PostgreSQL propriétaire des tables
(service `migrer`) :

1. efface le compte et **tout ce qui lui appartient** (annonces et leurs fichiers, conversations et messages, favoris,
   alertes, avis, notifications, appareils, abonnements, paiements, signalements qui le visent) ;
2. efface aussi **ses lignes du journal d'activité** (le journal est protégé : la commande suspend sa protection le
   temps de la suppression, dans une seule transaction qui s'annule en cas d'erreur) ;
3. laisse **une seule ligne de trace** dans le journal, sans aucune donnée personnelle : l'identifiant du compte, son rôle
   et le nombre de lignes de journal effacées.

Garde-fous : le personnel (modérateurs, administrateurs) n'est jamais supprimé ; un compte qui a un paiement réussi
(vrai argent) est refusé sauf `--meme-payes` ; sans `--confirmer SUPPRIMER`, rien n'est effacé (simulation).

    immoplus run --rm migrer python manage.py supprimer_comptes_test --nom-utilisateur kofi.test
    immoplus run --rm migrer python manage.py supprimer_comptes_test --anonymises --confirmer SUPPRIMER
"""

import uuid
from collections import Counter

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.db.models import ProtectedError, RestrictedError

from apps.accounts.models import ROLES_PERSONNEL, GerantProfile, User
from apps.audit import services as audit
from apps.audit.models import AuditLog
from apps.billing.models import Transaction
from apps.listings.models import Listing
from apps.listings.services import medias

PROFONDEUR_MAX = 15
DECLENCHEUR = "audit_logs_pas_de_modification"


def _effacer(objet, decompte: Counter, profondeur: int = 0) -> None:
    """Supprime `objet`; chaque objet qui le protège (clé étrangère PROTECT) est supprimé d'abord, récursivement."""
    if profondeur > PROFONDEUR_MAX:
        raise CommandError("Chaîne de dépendances trop profonde : suppression annulée.")
    if not type(objet).objects.filter(pk=objet.pk).exists():
        return  # déjà parti avec un autre (suppression en cascade)
    while True:
        try:
            with transaction.atomic():
                _, detail = objet.delete()
        except (ProtectedError, RestrictedError) as erreur:
            bloquants = getattr(erreur, "protected_objects", None) or getattr(
                erreur, "restricted_objects", set()
            )
            if not bloquants:
                raise
            for bloquant in list(bloquants):
                _effacer(bloquant, decompte, profondeur + 1)
        else:
            decompte.update(detail)
            return


class Command(BaseCommand):
    help = "Supprime définitivement des comptes de test (simulation tant que --confirmer SUPPRIMER n'est pas donné)."

    def add_arguments(self, parser):
        parser.add_argument("--nom-utilisateur", action="append", default=[], metavar="NOM")
        parser.add_argument("--email", action="append", default=[], metavar="ADRESSE")
        parser.add_argument("--id", action="append", default=[], metavar="UUID")
        parser.add_argument(
            "--anonymises",
            action="store_true",
            help="Tous les comptes déjà supprimés par anonymisation (leurs restes de test).",
        )
        parser.add_argument(
            "--meme-payes",
            action="store_true",
            help="Accepte un compte qui a un paiement réussi (à n'utiliser que pour un essai en sandbox).",
        )
        parser.add_argument(
            "--confirmer", default="", help="Écrire SUPPRIMER pour exécuter vraiment."
        )

    # ------------------------------------------------------------------ sélection
    def _selection(self, options) -> list[User]:
        trouves: dict = {}
        for nom in options["nom_utilisateur"]:
            u = User.objects.filter(username__iexact=nom).first()
            if u is None:
                raise CommandError(f"Aucun compte avec le nom d'utilisateur « {nom} ».")
            trouves[u.pk] = u
        for adresse in options["email"]:
            u = User.objects.filter(email__iexact=adresse).first()
            if u is None:
                raise CommandError(f"Aucun compte avec l'adresse « {adresse} ».")
            trouves[u.pk] = u
        for identifiant in options["id"]:
            try:
                u = User.objects.filter(pk=uuid.UUID(identifiant)).first()
            except ValueError as erreur:
                raise CommandError(f"Identifiant invalide : {identifiant}") from erreur
            if u is None:
                raise CommandError(f"Aucun compte avec l'identifiant {identifiant}.")
            trouves[u.pk] = u
        if options["anonymises"]:
            for u in User.objects.filter(status="deleted", username__startswith="supprime."):
                trouves[u.pk] = u
        if not trouves:
            raise CommandError(
                "Aucun compte désigné (--nom-utilisateur, --email, --id ou --anonymises)."
            )
        return list(trouves.values())

    def _verifier(self, comptes: list[User], options) -> None:
        for u in comptes:
            if u.role in ROLES_PERSONNEL:
                raise CommandError(f"{u.username or u.email} est un compte du personnel : refusé.")
            if (
                not options["meme_payes"]
                and Transaction.objects.filter(user=u, status="succeeded").exists()
            ):
                raise CommandError(
                    f"{u.username or u.pk} a un paiement réussi : refusé (ajoute --meme-payes si c'est un essai)."
                )

    # ------------------------------------------------------------------ exécution
    def _supprimer(self, comptes: list[User], reel: bool) -> tuple[Counter, int]:
        decompte: Counter = Counter()
        lignes_journal = 0
        with connection.cursor() as c:
            c.execute(
                f"ALTER TABLE audit_logs DISABLE TRIGGER {DECLENCHEUR}"
            )  # annulé avec la transaction
        for u in comptes:
            profil = GerantProfile.objects.filter(user=u).first()
            if (
                profil is not None and reel
            ):  # les fichiers ne se « re-créent » pas : jamais en simulation
                for annonce in Listing.objects.filter(gerant_id=profil.pk):
                    medias.supprimer_tous(annonce)  # fichiers photos et vidéos
            lignes_journal += AuditLog.objects.filter(actor=u).count()
            lignes_journal += AuditLog.objects.filter(target_id=str(u.pk)).count()
            AuditLog.objects.filter(target_id=str(u.pk)).delete()
            _effacer(u, decompte)
        with connection.cursor() as c:
            c.execute(
                "SET CONSTRAINTS ALL IMMEDIATE"
            )  # les vérifications de clés se font avant de remettre la garde
            c.execute(f"ALTER TABLE audit_logs ENABLE TRIGGER {DECLENCHEUR}")
        return decompte, lignes_journal

    def handle(self, *args, **options):
        comptes = self._selection(options)
        self._verifier(comptes, options)
        reel = options["confirmer"] == "SUPPRIMER"
        self.stdout.write(f"{len(comptes)} compte(s) désigné(s) :")
        for u in comptes:
            self.stdout.write(f"  - {u.username or u.email or u.pk} ({u.role}, {u.status})")
        identites = [(str(u.pk), u.role) for u in comptes]
        try:
            with transaction.atomic():
                decompte, lignes_journal = self._supprimer(comptes, reel)
                if reel:
                    for identifiant, role in identites:
                        audit.enregistrer(
                            "compte.supprime_definitivement",
                            metadata={"id": identifiant, "role": role, "par": "commande"},
                        )
                else:
                    transaction.set_rollback(True)  # simulation : tout est annulé
        except ProtectedError as erreur:
            raise CommandError(f"Suppression impossible : {erreur}") from erreur
        self.stdout.write("Lignes effacées par table :")
        for modele, nombre in sorted(decompte.items()):
            self.stdout.write(f"  {modele} : {nombre}")
        self.stdout.write(f"Lignes du journal d'activité effacées : {lignes_journal}")
        if reel:
            self.stdout.write(self.style.SUCCESS("Comptes supprimés définitivement."))
        else:
            self.stdout.write(
                self.style.WARNING(
                    "SIMULATION : rien n'a été effacé. Ajoute --confirmer SUPPRIMER pour exécuter."
                )
            )
