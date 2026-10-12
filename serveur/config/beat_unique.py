"""Lance `celery beat` seulement si le verrou est pris ; l'arrête dès que le verrou est perdu."""

import subprocess  # nosec B404
import sys
import time

import redis

from apps.core.verrou import VerrouRedis
from config import env

CLE = "logeo:verrou:beat"


def main() -> int:
    client = redis.Redis.from_url(env.texte("REDIS_QUEUE_URL", "redis://localhost:6379/1"))
    verrou = VerrouRedis(client, CLE, duree_s=30)
    while not verrou.acquerir():
        sys.stderr.write("beat : une autre instance détient le verrou, attente.\n")
        time.sleep(10)
    # Commande constante, aucune entrée externe : les alertes B603 et B607 sont sans objet.
    processus = subprocess.Popen(  # noqa: S603  # nosec B603 B607
        [  # noqa: S607
            "celery",
            "-A",
            "config.celery",
            "beat",
            "-l",
            "info",
            "--schedule=/var/lib/logeo/celerybeat-schedule",
        ]
    )
    try:
        while processus.poll() is None:
            time.sleep(10)
            if not verrou.renouveler():
                sys.stderr.write("beat : verrou perdu, arrêt.\n")
                processus.terminate()
                return 1
        return processus.returncode or 0
    finally:
        verrou.liberer()


if __name__ == "__main__":
    sys.exit(main())
