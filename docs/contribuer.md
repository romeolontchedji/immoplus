# Contribuer à Immo+

## 1. Mise en place

```bash
make hooks     # active les hooks Git du dossier .githooks/
make installer # environnement Python local
```

Les hooks vérifient le format des commits et des branches, les noms de fichiers, l'hygiène (secrets, `print`) et, avant un
push, l'ensemble des contrôles. **N'utilise jamais `--no-verify`** : la CI refait les mêmes contrôles et refuse la fusion.

## 2. Travailler

1. Crée une branche : `git switch -c feat/messagerie-envoi-message` (modèle : `type/mots-en-minuscules-separes-par-des-tirets`).
2. Fais des commits cohérents : `feat(messagerie): envoyer un message`, puis une ligne `Refs: EF-MSG-03` pour `feat` et `fix`.
3. `make verifier` avant de pousser, puis `git push -u origin <branche>` et ouvre une demande de fusion (titre au même format).
4. Mets à jour `docs/avancement.md` à la fin de chaque session.

Fusion : classique ou « rebase », **jamais « squash »** (l'historique propre est la règle).

## 3. Premier push (amorçage)

Le hook refuse tout push sur `main`. Pour le tout premier push d'un dépôt vide, une seule fois :

```bash
IMMOPLUS_PREMIER_PUSH=1 git push -u origin main
```

## 4. Protéger `main` côté GitHub (obligatoire : les hooks locaux se contournent)

Dans *Settings → Branches → Add rule* pour `main`, ou en ligne de commande (remplace `OWNER/REPO`) :

```bash
gh api -X PUT repos/OWNER/REPO/branches/main/protection --input - <<'JSON'
{
  "required_status_checks": {"strict": true, "contexts": ["commits", "verifier", "image"]},
  "enforce_admins": true,
  "required_pull_request_reviews": {"required_approving_review_count": 1, "require_code_owner_reviews": true},
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_linear_history": false
}
JSON
```

Puis, dans *Settings → General → Pull Requests*, décoche « Allow squash merging ».
Dans `.github/CODEOWNERS`, remplace `@porteur-du-projet` par ton identifiant GitHub.
Les noms exacts des contrôles (`commits`, `verifier`, `image`) sont ceux des jobs des workflows ; vérifie-les dans l'onglet *Actions*
après la première exécution.

## 5. Ajouter une dépendance

Interdit sans ADR (`docs/adr/`). Ajoute-la dans `serveur/requirements/base.in` ou `dev.in`, régénère les fichiers `.txt`
avec `pip freeze` dans un environnement propre, et explique le choix.

## 6. Dépannage

`make diagnostic` affiche l'état de l'environnement. Le guide `docs/aide-ia-depannage.md` (phase 9) en détaillera les cas.
