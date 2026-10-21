"""Mesure de charge minimale : N connexions en parallèle sur une adresse pendant D secondes (docs/capacite.md).

Bibliothèque standard seulement. À lancer depuis le serveur ou un poste proche, jamais contre un site qui n'est pas
le nôtre. Les pages anonymes sont plafonnées par adresse IP (`RATE_IP_FACTOR`) : un « 429 » mesure la limite, pas le
serveur.

    python3 outils/mesurer_charge.py https://www.immoplus.bj/annonces --fils 10 --duree 15
"""

import argparse
import collections
import http.client
import sys
import threading
import time
import urllib.parse


def mesurer(url: str, fils: int, duree: float) -> dict:
    cible = urllib.parse.urlsplit(url)
    classe = http.client.HTTPSConnection if cible.scheme == "https" else http.client.HTTPConnection
    chemin = cible.path or "/"
    if cible.query:
        chemin += "?" + cible.query
    latences, codes, verrou = [], collections.Counter(), threading.Lock()
    fin = time.monotonic() + duree

    def boucle():
        connexion = classe(cible.netloc, timeout=30)
        while time.monotonic() < fin:
            debut = time.perf_counter()
            try:
                connexion.request("GET", chemin, headers={"Accept": "text/html,application/json"})
                reponse = connexion.getresponse()
                reponse.read()
                code = reponse.status
            except (OSError, http.client.HTTPException) as erreur:
                code = type(erreur).__name__
                connexion = classe(cible.netloc, timeout=30)
            with verrou:
                latences.append(time.perf_counter() - debut)
                codes[code] += 1

    travailleurs = [threading.Thread(target=boucle) for _ in range(fils)]
    for t in travailleurs:
        t.start()
    for t in travailleurs:
        t.join()
    latences.sort()
    n = len(latences) or 1
    return {
        "debit": len(latences) / duree,
        "mediane_ms": latences[n // 2] * 1000 if latences else 0,
        "p95_ms": latences[int(n * 0.95)] * 1000 if latences else 0,
        "codes": dict(codes),
    }


def main(argv: list[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("url")
    parseur.add_argument("--fils", type=int, default=10, help="connexions simultanées")
    parseur.add_argument("--duree", type=float, default=15, help="secondes")
    args = parseur.parse_args(argv)
    r = mesurer(args.url, args.fils, args.duree)
    sys.stdout.write(
        f"{args.url} ({args.fils} en parallèle) : {r['debit']:.0f} requêtes/s, médiane {r['mediane_ms']:.0f} ms, "
        f"95 % sous {r['p95_ms']:.0f} ms, codes {r['codes']}\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
