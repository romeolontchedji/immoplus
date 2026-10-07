"""Extensions PostgreSQL (CDC §8.3) : recherche approximative et insensible aux accents."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("core", "0001_initial")]
    operations = [
        migrations.RunSQL("CREATE EXTENSION IF NOT EXISTS pg_trgm;", reverse_sql=migrations.RunSQL.noop),
        migrations.RunSQL("CREATE EXTENSION IF NOT EXISTS unaccent;", reverse_sql=migrations.RunSQL.noop),
    ]
