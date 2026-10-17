"""Génère les jetons de design du site et du mobile depuis docs/design/tokens.json (plan d'actions v2, §1.3).

    python outils/construire_tokens.py            # écrit les fichiers générés
    python outils/construire_tokens.py --verifier # échoue (code 1) s'ils ne sont pas à jour

Site : bloc marqué en tête du premier `:root` de serveur/web/static/css/tokens.css (les autres jetons, dérivés ou
propres au site, restent écrits à la main dans ce fichier). Mobile : mobile/src/ui/theme/jetons.genere.ts.
"""

import json
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
SOURCE = RACINE / "docs/design/tokens.json"
CSS = RACINE / "serveur/web/static/css/tokens.css"
TS = RACINE / "mobile/src/ui/theme/jetons.genere.ts"
DEBUT, FIN = (
    "  /* <jetons-generes> ne pas modifier : docs/design/tokens.json, make jetons */",
    "  /* </jetons-generes> */",
)
RAYONS_CSS = {
    "field": "r-field",
    "card": "r-card",
    "card-l": "r-card-l",
    "sheet": "r-sheet",
    "pill": "r-pill",
}


def _rem(px: int) -> str:
    return f"{px / 16:g}rem"


def variables_css(j: dict) -> list[tuple[str, str]]:
    v = [(f"--{nom}", valeur) for nom, valeur in j["couleurs"].items()]
    v += [(f"--sp-{k}", _rem(px)) for k, px in j["espaces"].items()]
    v += [(f"--{RAYONS_CSS[k]}", f"{px}px") for k, px in j["rayons"].items()]
    v += [(f"--fs-{k}", _rem(px)) for k, px in j["tailles"].items()]
    return v


def css(j: dict, actuel: str) -> str:
    variables = variables_css(j)
    debut_root = actuel.index(":root {") + len(":root {")
    fin_root = actuel.index("\n}", debut_root)
    corps = actuel[debut_root:fin_root]
    corps = re.sub(re.escape(DEBUT) + r".*?" + re.escape(FIN) + r"\n?", "", corps, flags=re.S)
    motifs = [re.compile(r"[ \t]*" + re.escape(nom) + r":[^;]*;") for nom, _ in variables]
    lignes = []
    for ligne in corps.split("\n"):  # une seule définition : celle du bloc généré
        nouvelle = ligne
        for motif in motifs:
            nouvelle = motif.sub("", nouvelle)
        if nouvelle != ligne and not re.sub(r"/\*.*?\*/", "", nouvelle).strip():
            continue  # ligne vidée par le retrait (commentaire de fin de ligne compris)
        lignes.append(nouvelle)
    corps = "\n".join(lignes)
    bloc = "\n".join([DEBUT, *[f"  {nom}: {valeur};" for nom, valeur in variables], FIN])
    return actuel[:debut_root] + "\n" + bloc + corps + actuel[fin_root:]


def typescript(j: dict) -> str:
    cle = lambda k: k if re.fullmatch(r"[a-z]\w*", k) else json.dumps(k)  # noqa: E731
    camel = lambda k: re.sub(r"-(\w)", lambda m: m.group(1).upper(), k)  # noqa: E731
    lignes = [
        "/* Fichier généré par outils/construire_tokens.py depuis docs/design/tokens.json : ne pas modifier. */",
        "",
    ]
    lignes.append("export const jetons = {")
    lignes.append("  couleurs: {")
    lignes += [f'    {camel(k)}: "{v}",' for k, v in j["couleurs"].items()]
    lignes.append("  },")
    for groupe in ("espaces", "rayons", "tailles"):
        lignes.append(f"  {groupe}: {{")
        lignes += [f"    {cle(camel(k))}: {v}," for k, v in j[groupe].items()]
        lignes.append("  },")
    lignes.append("} as const;")
    return "\n".join(lignes) + "\n"


def main() -> int:
    j = json.loads(SOURCE.read_text(encoding="utf-8"))
    attendus = {CSS: css(j, CSS.read_text(encoding="utf-8")), TS: typescript(j)}
    if "--verifier" in sys.argv:
        perimes = [
            str(p.relative_to(RACINE))
            for p, contenu in attendus.items()
            if not p.exists() or p.read_text(encoding="utf-8") != contenu
        ]
        if perimes:
            sys.stdout.write(
                f"Jetons de design pas à jour (lancer « make jetons ») : {', '.join(perimes)}\n"
            )
            return 1
        sys.stdout.write("Jetons de design à jour.\n")
        return 0
    for chemin, contenu in attendus.items():
        chemin.write_text(contenu, encoding="utf-8")
        sys.stdout.write(f"écrit : {chemin.relative_to(RACINE)}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
