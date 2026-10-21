import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import construire_css  # noqa: E402
import contraste  # noqa: E402


class TestContraste(unittest.TestCase):
    def test_noir_sur_blanc(self):
        self.assertAlmostEqual(contraste.rapport("#000000", "#FFFFFF"), 21.0, places=1)

    def test_identique(self):
        self.assertAlmostEqual(contraste.rapport("#117853", "#117853"), 1.0, places=2)

    def test_les_jetons_reels_sont_conformes(self):
        self.assertEqual(contraste.verifier(), [])

    def test_detecte_un_contraste_insuffisant(self):
        original = contraste.TOKENS
        with tempfile.TemporaryDirectory() as d:
            faux = Path(d) / "tokens.css"
            css = original.read_text(encoding="utf-8").replace(
                "--text-muted: var(--sable-600);", "--text-muted: var(--sable-300);"
            )
            faux.write_text(css, encoding="utf-8")
            contraste.TOKENS = faux
            try:
                erreurs = contraste.verifier()
            finally:
                contraste.TOKENS = original
        self.assertTrue(any("texte atténué" in e and "clair" in e for e in erreurs))

    def test_detecte_deux_themes_sombres_divergents(self):
        original = contraste.TOKENS
        with tempfile.TemporaryDirectory() as d:
            faux = Path(d) / "tokens.css"
            css = original.read_text(encoding="utf-8")
            css = css.replace(
                ':root[data-theme="dark"] {\n  --bg: var(--sable-950);',
                ':root[data-theme="dark"] {\n  --bg: #123456;',
            )
            faux.write_text(css, encoding="utf-8")
            contraste.TOKENS = faux
            try:
                erreurs = contraste.verifier()
            finally:
                contraste.TOKENS = original
        self.assertTrue(any("diffèrent" in e for e in erreurs))


class TestConstruireCss(unittest.TestCase):
    def test_minifie(self):
        self.assertEqual(construire_css.minifier("a {\n  color: red; /* x */\n}\n"), "a{color:red}")

    def test_conserve_le_selecteur_descendant_avec_pseudo_classe(self):
        self.assertEqual(construire_css.minifier("a :hover { color: red; }"), "a :hover{color:red}")

    def test_conserve_calc(self):
        self.assertIn("calc(1px + 2px)", construire_css.minifier("a { width: calc(1px + 2px); }"))

    def test_assemblage_en_couches_dans_l_ordre(self):
        css = construire_css.assembler()
        positions = [css.index(f"@layer {n}{{") for n in construire_css.COUCHES]
        self.assertEqual(positions, sorted(positions))
        self.assertTrue(css.startswith("@layer tokens, base, layout, components, utilities;"))

    def test_empreinte_et_manifeste(self):
        sortie = construire_css.construire()
        manifeste = json.loads((construire_css.DIST / "manifest.json").read_text())
        self.assertEqual(manifeste["immoplus.css"], f"css/dist/{sortie.name}")
        self.assertRegex(sortie.name, r"^immoplus\.[0-9a-f]{10}\.css$")
        self.assertEqual(len(list(construire_css.DIST.glob("immoplus.*.css"))), 1)

    def test_construction_deterministe(self):
        self.assertEqual(construire_css.construire().name, construire_css.construire().name)

    def test_aucune_couleur_en_dur_hors_des_jetons(self):
        import re

        fautes = []
        for f in sorted(construire_css.SOURCES.rglob("*.css")):
            if f.name == "tokens.css" or "dist" in f.parts:
                continue
            for n, ligne in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                if re.search(r"#[0-9a-fA-F]{3,8}\b|\brgba?\(", ligne):
                    fautes.append(f"{f.name}:{n}")
        self.assertEqual(fautes, [], "couleur en dur hors de tokens.css")


if __name__ == "__main__":
    unittest.main()
