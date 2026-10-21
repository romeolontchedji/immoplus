"""Modèles des comptes : utilisateurs, appareils, profils de gérants (CDC §9.3 à §9.6, ADR 0009)."""

import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models
from django.db.models.functions import Lower, Now
from django.utils import timezone

from .enums import (  # noqa: F401  (réexportées : l'import historique depuis `models` continue de fonctionner)
    ROLES_CLIENTELE,
    ROLES_PERSONNEL,
    FournisseurPush,
    Occupation,
    Plateforme,
    Role,
    Statut,
    StatutVerification,
    TypePiece,
)


def _in(champ: str, valeurs) -> str:
    return ", ".join(f"'{v}'" for v in valeurs)


class UserManager(BaseUserManager):
    use_in_migrations = False

    def creer_personnel(
        self, *, email: str, password: str, full_name: str, role: str = Role.MODERATOR
    ):
        """Crée un compte du personnel (ligne de commande ou administration, jamais l'API publique)."""
        if role not in ROLES_PERSONNEL:
            raise ValueError("Le personnel est modérateur ou administrateur.")
        utilisateur = self.model(email=self.normalize_email(email), full_name=full_name, role=role)
        utilisateur.set_password(password)
        utilisateur.save(using=self._db)
        return utilisateur


class User(AbstractBaseUser):
    """Locataires, gérants et personnel dans une seule table ; le personnel n'ouvre que l'administration."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Clé du compte (ADR 0009) : unique sans tenir compte des majuscules ; absent pour le personnel et pour un
    # gérant qui n'a pas encore activé son compte.
    username = models.CharField(
        max_length=30, null=True, blank=True, verbose_name="nom d'utilisateur"
    )
    email = models.EmailField(
        max_length=254, unique=True, null=True, blank=True, verbose_name="e-mail"
    )
    email_verified_at = models.DateTimeField(
        null=True, blank=True, verbose_name="e-mail confirmé le"
    )
    password = models.CharField("password", max_length=255, db_column="password_hash")
    first_name = models.CharField(max_length=60, default="", db_default="", verbose_name="prénom")
    last_name = models.CharField(max_length=60, default="", db_default="", verbose_name="nom")
    # « Prénom Nom », tenu à jour par `definir_noms` : reste la forme affichée partout.
    full_name = models.CharField(max_length=120, verbose_name="nom complet")
    # Clé de secours du mot de passe oublié (ADR 0009) : seule son empreinte Argon2 est gardée.
    recovery_key_hash = models.CharField(
        max_length=255, null=True, blank=True, verbose_name="empreinte de la clé de secours"
    )
    recovery_key_created_at = models.DateTimeField(
        null=True, blank=True, verbose_name="clé de secours créée le"
    )
    occupation = models.CharField(
        max_length=16, choices=Occupation.choices, null=True, blank=True, verbose_name="tu es"
    )
    role = models.CharField(max_length=12, choices=Role.choices, verbose_name="rôle")
    status = models.CharField(
        max_length=12,
        choices=Statut.choices,
        default=Statut.ACTIVE,
        db_default="active",
        verbose_name="statut",
    )
    suspended_until = models.DateTimeField(null=True, blank=True, verbose_name="suspendu jusqu'au")
    avatar_path = models.CharField(max_length=255, null=True, blank=True, verbose_name="photo")
    token_version = models.IntegerField(default=0, db_default=0, verbose_name="version de sécurité")
    terms_version = models.CharField(
        max_length=16, null=True, blank=True, verbose_name="version des conditions"
    )
    terms_accepted_at = models.DateTimeField(
        null=True, blank=True, verbose_name="conditions acceptées le"
    )
    notif_prefs = models.JSONField(default=dict, db_default={})
    last_seen_at = models.DateTimeField(null=True, blank=True, verbose_name="dernière activité")
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="supprimé le")
    created_at = models.DateTimeField(
        default=timezone.now, db_default=Now(), verbose_name="créé le"
    )
    updated_at = models.DateTimeField(auto_now=True, db_default=Now(), verbose_name="modifié le")

    last_login = None  # supprimé : voir `last_seen_at`
    USERNAME_FIELD = "id"
    REQUIRED_FIELDS: list[str] = []
    objects = UserManager()

    class Meta:
        db_table = "users"
        verbose_name = "compte"
        verbose_name_plural = "comptes"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(role__in=[r.value for r in Role]), name="users_role_valide"
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=[s.value for s in Statut]), name="users_status_valide"
            ),
            models.CheckConstraint(
                condition=models.Q(occupation__isnull=True)
                | models.Q(occupation__in=[o.value for o in Occupation]),
                name="users_occupation_valide",
            ),
            models.CheckConstraint(
                condition=~models.Q(role__in=["moderator", "admin"])
                | models.Q(email__isnull=False),
                name="users_personnel_a_un_email",
            ),
            models.CheckConstraint(
                condition=~models.Q(role="client") | models.Q(username__isnull=False),
                name="users_locataire_a_un_nom_utilisateur",
            ),
            models.CheckConstraint(
                condition=models.Q(username__isnull=True)
                | models.Q(username__regex=r"^[a-z0-9][a-z0-9._]{1,28}[a-z0-9]$"),
                name="users_nom_utilisateur_valide",
            ),
            models.UniqueConstraint(Lower("username"), name="users_nom_utilisateur_unique"),
        ]
        indexes = [
            models.Index(fields=["role", "status"], name="users_role_status_idx"),
        ]

    def __str__(self) -> str:
        return self.full_name or self.username or str(self.id)

    def definir_noms(self, prenom: str, nom: str) -> None:
        """Prénom et nom séparés (ADR 0009) ; `full_name` garde la forme affichée « Prénom Nom »."""
        self.first_name = " ".join((prenom or "").split())[:60]
        self.last_name = " ".join((nom or "").split())[:60]
        self.full_name = f"{self.first_name} {self.last_name}".strip()[:120]

    def get_full_name(self) -> str:
        return self.full_name or self.email or ""

    def get_short_name(self) -> str:
        """Salutation de l'administration (« Bienvenue, Awa ») au lieu de l'identifiant technique."""
        return self.prenom or self.get_full_name()

    # --- Droits : déduits du rôle, jamais d'un champ modifiable par l'application publique ---
    @property
    def is_staff(self) -> bool:
        return self.role in ROLES_PERSONNEL and self.is_active

    @property
    def is_superuser(self) -> bool:
        return self.role == Role.ADMIN and self.is_active

    @property
    def initiales(self) -> str:
        if self.full_name:
            parties = self.full_name.strip().split()
            if len(parties) >= 2:
                return f"{parties[0][0]}{parties[1][0]}".upper()
            return parties[0][:2].upper()
        return "U"

    @property
    def prenom(self) -> str:
        if self.first_name:
            return self.first_name
        if self.full_name:
            return self.full_name.strip().split()[0]
        return ""

    @property
    def est_personnel(self) -> bool:
        return self.role in ROLES_PERSONNEL

    @property
    def is_active(self) -> bool:
        if self.status == Statut.ACTIVE:
            return True
        if (
            self.status == Statut.SUSPENDED
            and self.suspended_until
            and self.suspended_until <= timezone.now()
        ):
            return (
                True  # suspension échue : la réactivation en base est faite par la tâche planifiée
            )
        return False

    def has_perm(self, perm: str, obj=None) -> bool:
        from apps.accounts.permissions_personnel import autorise

        return autorise(self, perm)

    def has_module_perms(self, app_label: str) -> bool:
        from apps.accounts.permissions_personnel import autorise_module

        return autorise_module(self, app_label)


class Device(models.Model):
    """Une installation connectée : jeton de rafraîchissement, jeton de notification, dernière activité."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="devices")
    installation_id = models.CharField(max_length=64)
    platform = models.CharField(max_length=8, choices=Plateforme.choices)
    app_version = models.CharField(max_length=20, null=True, blank=True)
    label = models.CharField(max_length=120, null=True, blank=True)
    refresh_hash = models.CharField(max_length=64, unique=True, null=True, blank=True)
    prev_refresh_hash = models.CharField(max_length=64, null=True, blank=True)
    refresh_expires_at = models.DateTimeField()
    push_provider = models.CharField(
        max_length=8, choices=FournisseurPush.choices, null=True, blank=True
    )
    push_token = models.TextField(null=True, blank=True)
    push_invalid_at = models.DateTimeField(null=True, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    last_ip = models.GenericIPAddressField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_default=Now())
    # Date du dernier échange de jeton : sert à la grâce de 60 s (colonne technique, non exposée).
    rotated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "devices"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "installation_id"], name="devices_utilisateur_installation_uq"
            ),
            models.CheckConstraint(
                condition=models.Q(platform__in=[p.value for p in Plateforme]),
                name="devices_plateforme_valide",
            ),
            models.CheckConstraint(
                condition=models.Q(push_provider__isnull=True)
                | models.Q(push_provider__in=[f.value for f in FournisseurPush]),
                name="devices_push_fournisseur_valide",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "revoked_at"], name="devices_user_revoked_idx"),
            # Détection de réutilisation d'un ancien jeton de rafraîchissement (hors du modèle du CDC §9.5).
            models.Index(
                fields=["prev_refresh_hash"],
                name="devices_prev_refresh_idx",
                condition=models.Q(prev_refresh_hash__isnull=False),
            ),
        ]


# Colonnes que le rôle PostgreSQL `app` ne peut pas lire (pièces et notes : administration seulement).
COLONNES_RESERVEES_ADMIN = (
    "interview_notes",
    "id_doc_type",
    "id_doc_path",
    "extra_doc_path",
    "docs_retain_until",
)


class GerantProfileManager(models.Manager):
    """Par défaut, les colonnes réservées à l'administration ne sont pas chargées (le rôle `app` ne peut pas les lire)."""

    def get_queryset(self):
        return super().get_queryset().defer(*COLONNES_RESERVEES_ADMIN)


class GerantProfile(models.Model):
    """Extension 1-1 d'un compte gérant. Pièces chiffrées lisibles depuis l'administration seulement."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="gerant_profile",
        verbose_name="compte",
    )
    display_name = models.CharField(
        max_length=120, null=True, blank=True, verbose_name="nom affiché"
    )
    zone = models.CharField(max_length=160, verbose_name="zone")
    verification_status = models.CharField(
        max_length=12,
        choices=StatutVerification.choices,
        default=StatutVerification.PENDING,
        db_default="pending",
        verbose_name="vérification",
    )
    verified_at = models.DateTimeField(null=True, blank=True, verbose_name="vérifié le")
    verified_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        db_column="verified_by",
        verbose_name="vérifié par",
    )
    interview_notes = models.TextField(null=True, blank=True)
    id_doc_type = models.CharField(max_length=20, choices=TypePiece.choices, null=True, blank=True)
    id_doc_path = models.CharField(max_length=255, null=True, blank=True)
    extra_doc_path = models.CharField(max_length=255, null=True, blank=True)
    docs_retain_until = models.DateField(null=True, blank=True)
    response_rate_30d = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="taux de réponse (30 j)"
    )
    median_response_min = models.IntegerField(
        null=True, blank=True, verbose_name="délai médian de réponse (min)"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="+",
        db_column="created_by",
        verbose_name="créé par",
    )
    created_at = models.DateTimeField(
        default=timezone.now, db_default=Now(), verbose_name="créé le"
    )
    updated_at = models.DateTimeField(auto_now=True, db_default=Now(), verbose_name="modifié le")

    def __str__(self) -> str:
        return self.display_name or getattr(self.user, "full_name", "") or "Gérant"

    objects = GerantProfileManager()
    complets = models.Manager()  # administration : toutes les colonnes

    class Meta:
        db_table = "gerant_profiles"
        verbose_name = "gérant"
        verbose_name_plural = "gérants"
        # `annonce.gerant` (clé étrangère) passe par le gestionnaire de base : il doit lui aussi laisser de côté les
        # colonnes réservées, sinon le rôle `app` reçoit « permission denied for table gerant_profiles ».
        base_manager_name = "objects"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(verification_status__in=[s.value for s in StatutVerification]),
                name="gerant_profiles_verification_valide",
            ),
            models.CheckConstraint(
                condition=models.Q(id_doc_type__isnull=True)
                | models.Q(id_doc_type__in=[t.value for t in TypePiece]),
                name="gerant_profiles_piece_valide",
            ),
        ]
