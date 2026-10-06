"""Utilitaires communs aux contrôles : liste des fichiers suivis et lecture de leur contenu."""
import subprocess


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, check=True).stdout


def fichiers(indexe=False):
    """Fichiers à contrôler : ceux de l'index (pre-commit) ou tous les fichiers suivis."""
    if indexe:
        sortie = git("diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z")
    else:
        sortie = git("ls-files", "-z")
    return [c for c in sortie.decode("utf-8", "surrogateescape").split("\0") if c]


def contenu(chemin, indexe=False):
    """Contenu binaire d'un fichier (version indexée si demandé), ou None s'il est illisible."""
    try:
        if indexe:
            return git("show", f":{chemin}")
        with open(chemin, "rb") as f:
            return f.read()
    except (subprocess.CalledProcessError, OSError):
        return None


def texte(chemin, indexe=False):
    """Contenu texte UTF-8, ou None pour un fichier binaire."""
    brut = contenu(chemin, indexe)
    if brut is None or b"\0" in brut:
        return None
    try:
        return brut.decode("utf-8")
    except UnicodeDecodeError:
        return None
