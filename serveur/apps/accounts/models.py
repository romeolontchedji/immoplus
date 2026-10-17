"""Modèles des comptes : utilisateurs, codes à usage unique, appareils, profils de gérants (CDC §9.3 à §9.6)."""

import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models
from django.db.models.functions import Now
from django.utils import timezone

from .enums import (  # noqa: F401  (réexportées : l'import historique depuis `models` continue de fonctionner)
    ROLES_CLIENTELE,
    ROLES_PERSONNEL,
    FournisseurPush,
    Objet,
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
    phone_e164 = models.CharField(max_length=16, unique=True, null=True, blank=True)
    email = models.EmailField(max_length=254, unique=True, null=True, blank=True)
    phone_verified_at = models.DateTimeField(null=True, blank=True)
    password = models.CharField("password", max_length=255, db_column="password_hash")
    full_name = models.CharField(max_length=120)
    occupation = models.CharField(max_length=16, choices=Occupation.choices, null=True, blank=True)
    role = models.CharField(max_length=12, choices=Role.choices)
    status = models.CharField(
        max_length=12, choices=Statut.choices, default=Statut.ACTIVE, db_default="active"
    )
    suspended_until = models.DateTimeField(null=True, blank=True)
    avatar_path = models.CharField(max_length=255, null=True, blank=True)
    token_version = models.IntegerField(default=0, db_default=0)
    terms_version = models.CharField(max_length=16, null=True, blank=True)
    terms_accepted_at = models.DateTimeField(null=True, blank=True)
    notif_prefs = models.JSONField(default=dict, db_default={})
    last_seen_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_default=Now())
    updated_at = models.DateTimeField(auto_now=True, db_default=Now())

    last_login = None  # supprimé : voir `last_seen_at`
    USERNAME_FIELD = "id"
    REQUIRED_FIELDS: list[str] = []
    objects = UserManager()

    class Meta:
        db_table = "users"
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
                condition=~models.Q(role__in=["client", "gerant"])
                | models.Q(phone_e164__isnull=False),
                name="users_clientele_a_un_numero",
            ),
            models.CheckConstraint(
                condition=~models.Q(role__in=["moderator", "admin"])
                | models.Q(email__isnull=False),
                name="users_personnel_a_un_email",
            ),
        ]
        indexes = [models.Index(fields=["role", "status"], name="users_role_status_idx")]

    def __str__(self) -> str:
        return self.full_name or str(self.id)

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


class OtpCode(models.Model):
    """Un enregistrement par code envoyé : sert aussi à compter les envois et leur coût (budget, plafonds)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone_e164 = models.CharField(max_length=16)
    purpose = models.CharField(max_length=20, choices=Objet.choices)
    code_hmac = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    attempts = models.SmallIntegerField(default=0, db_default=0)
    consumed_at = models.DateTimeField(null=True, blank=True)
    installation_id = models.CharField(max_length=64, null=True, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    provider_ref = models.CharField(max_length=80, null=True, blank=True)
    unit_cost_xof = models.SmallIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_default=Now())

    class Meta:
        db_table = "otp_codes"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(purpose__in=[o.value for o in Objet]),
                name="otp_codes_objet_valide",
            ),
            models.CheckConstraint(
                condition=models.Q(attempts__gte=0, attempts__lte=5), name="otp_codes_essais_bornes"
            ),
        ]
        indexes = [
            models.Index(
                fields=["phone_e164", "purpose", "-created_at"], name="otp_phone_purpose_idx"
            ),
            models.Index(fields=["installation_id", "created_at"], name="otp_installation_idx"),
            models.Index(fields=["ip", "created_at"], name="otp_ip_idx"),
            models.Index(fields=["purpose", "created_at"], name="otp_purpose_date_idx"),
        ]


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
        User, on_delete=models.CASCADE, primary_key=True, related_name="gerant_profile"
    )
    display_name = models.CharField(max_length=120, null=True, blank=True)
    zone = models.CharField(max_length=160)
    verification_status = models.CharField(
        max_length=12,
        choices=StatutVerification.choices,
        default=StatutVerification.PENDING,
        db_default="pending",
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        db_column="verified_by",
    )
    interview_notes = models.TextField(null=True, blank=True)
    id_doc_type = models.CharField(max_length=20, choices=TypePiece.choices, null=True, blank=True)
    id_doc_path = models.CharField(max_length=255, null=True, blank=True)
    extra_doc_path = models.CharField(max_length=255, null=True, blank=True)
    docs_retain_until = models.DateField(null=True, blank=True)
    response_rate_30d = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    median_response_min = models.IntegerField(null=True, blank=True)
    created_by = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="+", db_column="created_by"
    )
    created_at = models.DateTimeField(default=timezone.now, db_default=Now())
    updated_at = models.DateTimeField(auto_now=True, db_default=Now())

    objects = GerantProfileManager()
    complets = models.Manager()  # administration : toutes les colonnes

    class Meta:
        db_table = "gerant_profiles"
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
