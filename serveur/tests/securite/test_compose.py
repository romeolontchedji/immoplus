"""Structure de la pile Compose : isolation réseau et volumes (CDC §4.3). Vérifie le fichier, pas un démarrage réel."""

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.securite
COMPOSE = Path(__file__).resolve().parents[3] / "infra" / "compose"


class Chargeur(yaml.SafeLoader):
    """Accepte les étiquettes de fusion de Compose (`!override`, `!reset`)."""


for etiquette in ("!override", "!reset"):
    Chargeur.add_constructor(
        etiquette,
        lambda c, n: (
            c.construct_sequence(n) if isinstance(n, yaml.SequenceNode) else c.construct_mapping(n)
        ),
    )


def charger(nom):
    return yaml.load((COMPOSE / nom).read_text(encoding="utf-8"), Loader=Chargeur)  # noqa: S506 - chargeur dérivé de SafeLoader


@pytest.fixture(scope="module")
def pile():
    return charger("docker-compose.yml")


@pytest.fixture(scope="module")
def prod():
    return charger("docker-compose.prod.yml")


SERVICES = {"postgres", "redis-cache", "redis-queue", "migrer", "web-api", "realtime", "admin", "worker",
            "worker-media", "beat", "backup", "caddy"}  # fmt: skip


def test_tous_les_services_attendus(pile):
    assert set(pile["services"]) == SERVICES


def test_reseau_interne_sans_internet(pile):
    assert pile["networks"]["interne"]["internal"] is True


def test_worker_media_sans_internet(pile):
    assert pile["services"]["worker-media"]["networks"] == ["interne"]


def test_seul_caddy_est_expose_a_l_hote(pile):
    for nom, service in pile["services"].items():
        if nom != "caddy":
            assert "ports" not in service, nom
    assert "exposition" in pile["services"]["caddy"]["networks"]
    assert all(
        "exposition" not in s.get("networks", [])
        for n, s in pile["services"].items()
        if n != "caddy"
    )


def test_donnees_uniquement_sur_le_reseau_interne(pile):
    for nom in (
        "postgres",
        "redis-cache",
        "redis-queue",
        "realtime",
        "admin",
        "beat",
        "worker-media",
    ):
        assert pile["services"][nom]["networks"] == ["interne"], nom


def test_internet_reserve_aux_services_qui_en_ont_besoin(pile):
    avec_sortie = {n for n, s in pile["services"].items() if "sortie" in s.get("networks", [])}
    assert avec_sortie == {"web-api", "worker", "backup"}


def volumes_de(service, nom_volume):
    return [v for v in service.get("volumes", []) if str(v).startswith(f"{nom_volume}:")]


def test_media_private_seulement_dans_admin_et_backup(pile):
    avec = {n for n, s in pile["services"].items() if volumes_de(s, "media_private")}
    assert avec == {"admin", "backup"}


def test_media_private_absent_en_production_hors_admin_et_backup(prod, pile):
    for nom, service in prod["services"].items():
        if nom not in {"admin", "backup"}:
            assert not volumes_de(service, "media_private"), nom


def test_worker_media_ne_monte_que_media_tmp_et_public(pile):
    montes = {str(v).split(":")[0] for v in pile["services"]["worker-media"]["volumes"]}
    assert montes == {"../../serveur", "media_tmp", "media_public"}


def test_production_ne_monte_aucun_code(prod):
    for nom, service in prod["services"].items():
        for volume in service.get("volumes", []):
            assert "serveur" not in str(volume).split(":")[0], f"{nom} monte le code source"


def test_production_utilise_les_reglages_stricts(prod):
    assert (
        prod["services"]["web-api"]["environment"]["DJANGO_SETTINGS_MODULE"]
        == "config.settings.public"
    )
    assert (
        prod["services"]["admin"]["environment"]["DJANGO_SETTINGS_MODULE"]
        == "config.settings.admin"
    )
    assert prod["services"]["web-api"]["environment"]["LOGEO_RELOAD"] == "0"


def test_developpement_admin_utilise_les_reglages_locaux(pile):
    assert (
        pile["services"]["admin"]["environment"]["DJANGO_SETTINGS_MODULE"]
        == "config.settings.admin_local"
    )


def test_postgres_et_redis_sans_port_publie(pile):
    for nom in ("postgres", "redis-cache", "redis-queue"):
        assert "ports" not in pile["services"][nom]


def test_cache_perdable_et_file_durable(pile):
    cache = " ".join(pile["services"]["redis-cache"]["command"])
    file = " ".join(pile["services"]["redis-queue"]["command"])
    assert "allkeys-lru" in cache and "--save" in cache
    assert "--appendonly yes" in file and "noeviction" in file


def test_chaque_service_applicatif_a_son_fichier_d_environnement(pile):
    for nom in (
        "migrer",
        "web-api",
        "realtime",
        "admin",
        "worker",
        "worker-media",
        "beat",
        "backup",
        "caddy",
        "postgres",
    ):
        for chemin in (
            pile["services"][nom]["env_file"]
            if isinstance(pile["services"][nom]["env_file"], list)
            else [pile["services"][nom]["env_file"]]
        ):
            assert (COMPOSE / f"{chemin}.example").exists(), chemin


def test_caddy_de_production_ouvre_https_et_http3(prod):
    assert set(prod["services"]["caddy"]["ports"]) == {"80:80", "443:443", "443:443/udp"}


def test_migrer_cree_tout_le_schema_avec_ses_propres_reglages(pile, prod):
    assert (
        pile["services"]["migrer"]["environment"]["DJANGO_SETTINGS_MODULE"]
        == "config.settings.migrer"
    )
    assert (
        prod["services"]["migrer"]["environment"]["DJANGO_SETTINGS_MODULE"]
        == "config.settings.migrer"
    )
