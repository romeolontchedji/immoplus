"""Choix entre copie du flux et réencodage rapide des vidéos (sans ffmpeg : on contrôle la commande)."""

from pathlib import Path

import pytest

from apps.media import traitement

pytestmark = pytest.mark.unitaire

BONNE = {
    "width": 1280, "height": 720, "duration_s": 20.0, "codec": "h264", "pix_fmt": "yuv420p", "fps": 30.0,
    "debit_k": 1800, "audio": "aac", "conteneur": ["mov", "mp4"], "pivote": False,
}  # fmt: skip


def commande(meta, **kw):
    return traitement.commande_conversion(Path("/in.mp4"), Path("/out.mp4"), meta, **kw)


def test_une_video_deja_au_bon_format_est_copiee():
    assert traitement.copie_suffisante(BONNE)
    cmd = commande(BONNE)
    assert "copy" in cmd and "libx264" not in cmd


@pytest.mark.parametrize(
    "changement",
    [
        {"height": 1080},  # trop grande : à réduire
        {"codec": "hevc"},  # iPhone récent : lecture mal assurée partout
        {"fps": 60.0},
        {"debit_k": 9000},
        {"audio": "opus"},
        {"pivote": True},  # rotation par métadonnée : seul un réencodage la redresse
        {"conteneur": ["webm"]},
    ],
)
def test_sinon_on_reencode_vite_et_leger(changement):
    meta = {**BONNE, **changement}
    assert not traitement.copie_suffisante(meta)
    cmd = commande(meta)
    assert "libx264" in cmd and "superfast" in cmd and "copy" not in cmd
    assert "-maxrate" in cmd and "-threads" in cmd


def filtre(meta):
    cmd = commande(meta)
    return cmd[cmd.index("-vf") + 1]


def test_la_cadence_est_plafonnee_seulement_si_elle_depasse_30():
    assert "fps=30" in filtre({**BONNE, "fps": 60.0, "height": 1080})
    assert "fps=" not in filtre({**BONNE, "height": 1080})


def test_reprise_par_reencodage_quand_la_copie_echoue():
    assert "libx264" in commande(BONNE, copier=False)
