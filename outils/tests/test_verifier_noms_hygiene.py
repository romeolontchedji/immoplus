import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import verifier_hygiene as vh  # noqa: E402
import verifier_noms as vn  # noqa: E402

CONF = vn.configuration()
MOT = "back" + "end"


class TestNoms(unittest.TestCase):
    def test_chemins_valides(self):
        for chemin in [
            "serveur/apps/accounts/models.py",
            "docs/guide-installation-pas-a-pas.md",
            "README.md",
            "serveur/web/templates/web/fil-annonces.html",
            "Makefile",
            ".github/ISSUE_TEMPLATE/bug.md",
            "serveur/apps/accounts/migrations/0001_initial.py",
            ".env.example",
        ]:
            self.assertEqual(vn.erreurs_chemin(chemin, CONF), [], chemin)

    def test_chemins_invalides(self):
        for chemin in [
            f"{MOT}/x.py",
            f"serveur/{MOT.capitalize()}/x.py",
            "serveur/MonModule/x.py",
            "serveur/apps/Mon_Fichier.py",
            "docs/Mon_Guide.md",
            "serveur/web/static/css/Tokens.css",
        ]:
            self.assertTrue(vn.erreurs_chemin(chemin, CONF), chemin)

    def test_contenu(self):
        self.assertTrue(vn.erreurs_contenu("serveur/x.py", f"mon_{MOT}_service = 1", CONF))
        self.assertEqual(
            vn.erreurs_contenu("serveur/x.py", "EMAIL_" + MOT.upper() + " = 'x'", CONF), []
        )
        self.assertEqual(vn.erreurs_contenu("AGENTS.md", f"jamais {MOT}/", CONF), [])


class TestHygiene(unittest.TestCase):
    def _texte(self, lignes, chemin="serveur/x.py"):
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            ancien = os.getcwd()
            os.chdir(d)
            try:
                os.makedirs(os.path.dirname(chemin) or ".", exist_ok=True)
                with open(chemin, "w", encoding="utf-8") as f:
                    f.write(lignes)
                return vh.erreurs_fichier(chemin, indexe=False)
            finally:
                os.chdir(ancien)

    def test_debogage(self):
        self.assertTrue(self._texte("pri" + "nt('x')\n"))
        self.assertTrue(self._texte("break" + "point()\n"))
        self.assertEqual(self._texte("logger.info('x')\nimprimer = 1\n"), [])

    def test_secrets(self):
        self.assertTrue(self._texte("cle = 'AKIA" + "ABCDEFGHIJKLMNOP'\n"))
        self.assertTrue(self._texte("PASS" + "WORD = 'mot-de-passe-long-123'\n"))
        self.assertTrue(self._texte("url = 'postgres://admin:" + "hunter22@db/x'\n"))
        self.assertEqual(self._texte("PASSWORD = os.environ['DB_PASSWORD']\n"), [])

    def test_env_et_sauvegardes(self):
        self.assertTrue(vh.est_env_reel(".env"))
        self.assertTrue(vh.est_env_reel(".env.prod"))
        self.assertFalse(vh.est_env_reel(".env.example"))
        self.assertTrue(self._texte("x", chemin="dump.sql.gz"))


if __name__ == "__main__":
    unittest.main()


class TestExceptionsDjango(unittest.TestCase):
    """Les chemins de modules imposés par Django sont tolérés ; le mot interdit reste refusé ailleurs."""

    def setUp(self):
        self.conf = vn.configuration()

    def test_moteur_de_session_tolere(self):
        ligne = 'SESSION_ENGINE = "django.contrib.sessions.backends.db"'
        self.assertEqual(vn.erreurs_contenu("serveur/config/x.py", ligne, self.conf), [])

    def test_moteur_de_base_tolere(self):
        ligne = '"ENGINE": "django.db.backends.postgresql",'
        self.assertEqual(vn.erreurs_contenu("serveur/config/x.py", ligne, self.conf), [])

    def test_le_mot_seul_reste_refuse(self):
        erreurs = vn.erreurs_contenu("serveur/apps/x.py", "dossier = 'backend/utils'", self.conf)
        self.assertEqual(len(erreurs), 1)
