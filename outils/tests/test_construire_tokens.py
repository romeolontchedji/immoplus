"""Les jetons générés (site et mobile) correspondent à docs/design/tokens.json."""

import subprocess
import sys
import unittest
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]


class TestJetons(unittest.TestCase):
    def test_fichiers_generes_a_jour(self):
        r = subprocess.run(
            [sys.executable, str(RACINE / "outils/construire_tokens.py"), "--verifier"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_une_seule_definition_par_jeton_dans_le_premier_root(self):
        css = (RACINE / "serveur/web/static/css/tokens.css").read_text(encoding="utf-8")
        racine = css[css.index(":root {") : css.index("\n}", css.index(":root {"))]
        for nom in ("--blue:", "--sp-4:", "--r-card:", "--fs-16:"):
            self.assertEqual(racine.count(nom), 1, nom)


if __name__ == "__main__":
    unittest.main()
