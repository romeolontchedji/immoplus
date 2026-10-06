# Matrice de vérification

Légende : Exécuté ✅ · Simulé ⚠️ · Non exécuté ⛔

## Phase 0 (partiellement réalisée : contrôles Git uniquement)

| Composant | État | Preuve |
|---|---|---|
| Validation des messages de commit (`verifier_commit.py`) | Exécuté ✅ | `python3 -m unittest discover -s outils/tests -q` → 13 tests, OK |
| Validation des noms de branche (`verifier_branche.py`) | Exécuté ✅ | idem |
| Contrôle des noms et mots interdits (`verifier_noms.py`) | Exécuté ✅ | idem + cas 4 ci-dessous |
| Contrôle d'hygiène : secrets, débogage, tailles (`verifier_hygiene.py`) | Exécuté ✅ | idem + cas 8 ci-dessous ; `gitleaks` absent, motifs maison seulement |
| Hooks `pre-commit`, `commit-msg`, `pre-push` | Exécuté ✅ | `bash outils/tester_hooks.sh` (sortie ci-dessous) |
| `outils/verifier_tout.sh` | Exécuté ⚠️ | ruff, djlint absents : étapes **sautées**, signalées comme telles ; `LOGEO_STRICT=1` les fait échouer |
| `outils/dans-docker.sh` | Non exécuté ⛔ | Docker absent ; commande : `outils/dans-docker.sh python3 --version` |
| Workflows GitHub Actions, protection de branche | Non écrits | prévu en phase 0 |
| Compose, Caddy, réglages Django, `AGENTS.md`, CSS, ADR 0001 | Non écrits | bloqués : pas de réseau, voir `environnement-generation.md` |

### Sortie de `outils/tester_hooks.sh`

```
Contrôles Logeo :
  ✔ noms et mots interdits
  ✔ hygiène (secrets, débogage, tailles)
  ✔ nom de la branche courante
  ⏭ ruff check — sauté (ruff absent)
  ⏭ ruff format --check — sauté (ruff absent)
  ⏭ djlint --check — sauté (djlint absent)
✔ Contrôles réussis (3 sauté(s)).
Cas 1 — message sans format

✗ Message de commit refusé :
  - En-tête invalide : « ajout truc ».
    Format attendu : type(portée): sujet
    Exemple :
    feat(messagerie): ajouter l'envoi de message

    Refs: EF-MSG-03

  Exemple valide :
    feat(messagerie): ajouter l'envoi de message

    Refs: EF-MSG-03

  ✔ cas 1 — commit « ajout truc » : refus comme attendu
Cas 2 — feat sans Refs

✗ Message de commit refusé :
  - Les commits feat/fix exigent une ligne « Refs: EF-XXX-NN[, ENF-XXX-NN] » ou « Refs: n/a ».

  Exemple valide :
    feat(messagerie): ajouter l'envoi de message

    Refs: EF-MSG-03

  ✔ cas 2 — feat sans Refs : refus comme attendu
Cas 3 — feat avec Refs
  ✔ cas 3 — feat avec Refs : succes comme attendu
Cas 4 — dossier interdit

✗ Contrôle des noms : refusé
  - backend/x.py : le chemin contient un mot interdit (« backend »). Le dossier s'appelle « serveur/ ».

  ✔ cas 4 — fichier dans un dossier interdit : refus comme attendu
Cas 5 — mauvaise branche
      ✗ Push annulé : nom de branche refusé (voir ci-dessus).
  ✔ cas 5 — push de Feat/Mauvais_Nom : refus comme attendu
Cas 6 — push direct sur main
      ✗ Push annulé : push direct sur « main » interdit. Crée une branche (ex. feat/mon-changement) et ouvre une demande de fusion.
  ✔ cas 6 — push direct sur main : refus comme attendu
Cas 7 — commit wip poussé
      ✗ Push annulé : le commit c90e23f0 ne respecte pas le format (voir ci-dessus).
  ✔ cas 7 — commit « wip » poussé : refus comme attendu
Cas 8 — secret

✗ Contrôle d'hygiène : refusé
  - c.py:1 : clé d'accès AWS détecté. Les secrets vont dans l'environnement, jamais dans le dépôt.

  ✔ cas 8 — fausse clé secrète (commit) : refus comme attendu
      ✗ Push annulé : les contrôles complets ont échoué (voir ci-dessus).
  ✔ cas 8 — fausse clé secrète (push après --no-verify) : refus comme attendu
Cas 9 — série valide
  ✔ cas 9 — série valide poussée : succes comme attendu

Résultat : 10 conforme(s), 0 non conforme(s).
```
