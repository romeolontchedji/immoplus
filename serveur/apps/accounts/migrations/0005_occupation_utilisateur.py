"""« Tu es » à l'inscription (décision V2, docs/plan-actions-v2.md) : colonne facultative `users.occupation`.

Les droits de `app` sur `users` sont accordés colonne par colonne (0002) : la nouvelle colonne doit l'être aussi,
sinon le site et l'API ne pourraient pas modifier le profil.
"""

from django.db import migrations, models

DROITS = r"""
DO $droits$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app') THEN
    GRANT UPDATE (occupation) ON users TO app;
  END IF;
END
$droits$;
"""

ANNULER_DROITS = r"""
DO $droits$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app') THEN
    REVOKE UPDATE (occupation) ON users FROM app;
  END IF;
END
$droits$;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0004_gestionnaire_base_profil_gerant"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="occupation",
            field=models.CharField(
                blank=True,
                choices=[
                    ("student_up", "Étudiant(e) à l'UP"),
                    ("student_other", "Étudiant(e) ailleurs"),
                    ("employee", "Salarié(e)"),
                    ("self_employed", "Indépendant(e)"),
                    ("other", "Autre"),
                ],
                max_length=16,
                null=True,
            ),
        ),
        migrations.AddConstraint(
            model_name="user",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("occupation__isnull", True),
                    (
                        "occupation__in",
                        [
                            "student_up",
                            "student_other",
                            "employee",
                            "self_employed",
                            "other",
                        ],
                    ),
                    _connector="OR",
                ),
                name="users_occupation_valide",
            ),
        ),
        migrations.RunSQL(DROITS, reverse_sql=ANNULER_DROITS),
    ]
