import base64
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import creer_env  # noqa: E402


class TestCreerEnv(unittest.TestCase):
    def test_genere_les_secrets_vides_et_conserve_les_autres(self):
        valeurs = creer_env.generer({"SITE_SECRET_KEY": "", "APP_DB_PASSWORD": "fixe"})
        self.assertGreaterEqual(len(valeurs["SITE_SECRET_KEY"]), 48)
        self.assertEqual(valeurs["APP_DB_PASSWORD"], "fixe")

    def test_cle_fernet_valide(self):
        cle = creer_env.generer({})["PRIVATE_FILES_KEY"]
        self.assertEqual(len(base64.urlsafe_b64decode(cle)), 32)

    def test_les_cles_du_site_et_de_l_administration_different(self):
        v = creer_env.generer({})
        self.assertNotEqual(v["SITE_SECRET_KEY"], v["ADMIN_SECRET_KEY"])
        self.assertNotEqual(v["SITE_SECRET_KEY"], v["JWT_SIGNING_KEY"])

    def test_rendu_remplace_les_marqueurs(self):
        self.assertEqual(creer_env.rendre("A={{X}}", {"X": "1"}), "A=1")

    def test_rendu_echoue_sur_variable_inconnue(self):
        with self.assertRaises(KeyError):
            creer_env.rendre("A={{INCONNUE}}", {})

    def test_tous_les_modeles_se_rendent_avec_le_modele_racine(self):
        valeurs = creer_env.generer(creer_env.lire_valeurs(creer_env.MODELE_RACINE))
        for modele in creer_env.DOSSIER_ENV.glob("*.env.example"):
            rendu = creer_env.rendre(modele.read_text(encoding="utf-8"), valeurs)
            self.assertNotIn("{{", rendu, modele.name)

    def test_cles_sensibles_limitees_aux_bons_services(self):
        def contient(nom, cle):
            return cle in (creer_env.DOSSIER_ENV / nom).read_text(encoding="utf-8")

        for service in ("admin", "backup"):
            self.assertTrue(contient(f"{service}.env.example", "PRIVATE_FILES_KEY"))
        for service in ("web-api", "realtime", "worker", "worker-media", "beat", "caddy", "migrer"):
            self.assertFalse(contient(f"{service}.env.example", "PRIVATE_FILES_KEY"), service)
        self.assertFalse(contient("admin.env.example", "SITE_SECRET_KEY"))
        self.assertFalse(contient("web-api.env.example", "ADMIN_SECRET_KEY"))

    def test_idempotence_dans_un_depot_temporaire(self):
        with tempfile.TemporaryDirectory() as d:
            racine = Path(d)
            (racine / "infra" / "compose" / "env").mkdir(parents=True)
            (racine / ".env.example").write_text("SITE_SECRET_KEY=\n", encoding="utf-8")
            (racine / "infra/compose/env/x.env.example").write_text(
                "K={{SITE_SECRET_KEY}}\n", encoding="utf-8"
            )
            avant = (creer_env.RACINE, creer_env.MODELE_RACINE, creer_env.DOSSIER_ENV)
            creer_env.RACINE = racine
            creer_env.MODELE_RACINE = racine / ".env.example"
            creer_env.DOSSIER_ENV = racine / "infra" / "compose" / "env"
            try:
                self.assertEqual(creer_env.main([]), 0)
                premier = (racine / "infra/compose/env/x.env").read_text()
                self.assertEqual(creer_env.main([]), 0)
                self.assertEqual((racine / "infra/compose/env/x.env").read_text(), premier)
                self.assertEqual((racine / ".env").stat().st_mode & 0o777, 0o600)
            finally:
                creer_env.RACINE, creer_env.MODELE_RACINE, creer_env.DOSSIER_ENV = avant

    def test_services_regeneres_sans_changer_les_secrets(self):
        with tempfile.TemporaryDirectory() as d:
            racine = Path(d)
            (racine / "infra" / "compose" / "env").mkdir(parents=True)
            (racine / ".env.example").write_text(
                "DOMAIN=localhost\nSITE_SECRET_KEY=\n", encoding="utf-8"
            )
            (racine / "infra/compose/env/x.env.example").write_text(
                "K={{SITE_SECRET_KEY}}\nD={{DOMAIN}}\n", encoding="utf-8"
            )
            avant = (creer_env.RACINE, creer_env.MODELE_RACINE, creer_env.DOSSIER_ENV)
            creer_env.RACINE = racine
            creer_env.MODELE_RACINE = racine / ".env.example"
            creer_env.DOSSIER_ENV = racine / "infra" / "compose" / "env"
            try:
                creer_env.main([])
                secret = creer_env.lire_valeurs(racine / ".env")["SITE_SECRET_KEY"]
                self.assertGreaterEqual(len(secret), 48)  # écrit dans .env dès le premier passage
                env = racine / ".env"
                env.write_text(env.read_text().replace("DOMAIN=localhost", "DOMAIN=immoplus.bj"))
                self.assertEqual(creer_env.main(["--services"]), 0)
                rendu = (racine / "infra/compose/env/x.env").read_text()
                self.assertIn("D=immoplus.bj", rendu)
                self.assertIn(f"K={secret}", rendu)
            finally:
                creer_env.RACINE, creer_env.MODELE_RACINE, creer_env.DOSSIER_ENV = avant


if __name__ == "__main__":
    unittest.main()
