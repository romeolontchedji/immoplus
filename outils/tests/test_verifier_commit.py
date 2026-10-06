import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import verifier_branche as vb  # noqa: E402
import verifier_commit as vc  # noqa: E402


class TestCommit(unittest.TestCase):
    def test_valides(self):
        self.assertEqual(
            vc.verifier("feat(messagerie): ajouter l'envoi de message\n\nRefs: EF-MSG-03"), []
        )
        self.assertEqual(
            vc.verifier("fix(api): corriger la pagination\n\nRefs: EF-MSG-03, ENF-PERF-02"), []
        )
        self.assertEqual(vc.verifier("fix(api): corriger la pagination\n\nRefs: n/a"), [])
        self.assertEqual(vc.verifier("docs(docs): décrire le guide d'installation"), [])
        self.assertEqual(vc.verifier("Merge branch 'main' into feat/x"), [])

    def test_invalides(self):
        for msg in [
            "ajout truc",
            "feat: sans portée",
            "feat(inconnue): sujet valide",
            "truc(web): sujet valide",
            "feat(web): Majuscule au début\n\nRefs: n/a",
            "docs(docs): point final.",
            "docs(docs): abc",
            "feat(serveur): ajouter l'envoi de message",
            "wip",
            "docs(docs): " + "x" * 80,
            "refactor(api)!: changer le format",
        ]:
            with self.subTest(msg=msg):
                self.assertTrue(vc.verifier(msg), msg)

    def test_refs_malformees(self):
        self.assertTrue(vc.verifier("feat(web): ajouter une page\n\nRefs: truc"))

    def test_fixup_local_ok_push_refuse(self):
        self.assertEqual(vc.verifier("fixup! feat(web): x"), [])
        self.assertTrue(vc.verifier("fixup! feat(web): x", push=True))

    def test_casse_avec_corps(self):
        self.assertEqual(
            vc.verifier("refactor(api)!: changer le format\n\nMigration : adapter le client."), []
        )


class TestBranche(unittest.TestCase):
    def test_noms(self):
        for ok in ["main", "feat/messagerie-envoi-message", "fix/a1", "chore/ci"]:
            self.assertIsNone(vb.erreur(ok), ok)
        for ko in [
            "Feat/Mauvais_Nom",
            "feature/x",
            "feat/avec_underscore",
            "feat/accentué",
            "feat/" + "a" * 60,
            "develop",
        ]:
            self.assertIsNotNone(vb.erreur(ko), ko)


class TestBrancheSansCommit(unittest.TestCase):
    def test_depot_vide(self):
        import subprocess
        import tempfile

        script = os.path.join(os.path.dirname(__file__), "..", "verifier_branche.py")
        with tempfile.TemporaryDirectory() as d:
            subprocess.run(["git", "init", "-q", "-b", "main", d], check=True)
            r = subprocess.run([sys.executable, script], cwd=d, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)


if __name__ == "__main__":
    unittest.main()
