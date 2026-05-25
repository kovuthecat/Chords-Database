"""
Tests Flask minimaux — app.py
Utilise app.test_client() ; pas de Selenium, pas de Playwright.

Les tests écrivent dans les dossiers réels data/ et output/ avec un slug de test isolé.
Nettoyage automatique avant et après chaque test.
"""
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Racine du projet sur le sys.path pour que "import app" fonctionne
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import app as flask_app
from config import DATA_DIR, OUTPUT_DIR
from backup import BACKUP_DIR

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TEST_SLUG = "test-p9-flask"

VALID_SONG: dict = {
    "meta": {
        "title": "Test Song P9",
        "artist": "Test Artist",
        "slug": TEST_SLUG,
    },
    "chords_used": ["Am", "C", "G"],
    "structure_sequence": ["intro_1", "verse_1"],
    "sections": [
        {
            "id": "intro_1",
            "type": "intro",
            "label": "Intro",
            "is_instrumental": True,
            "repeats": 1,
            "lines": [],
            "performance_progression": [{"chords": "Am C G", "repeat": 2}],
        },
        {
            "id": "verse_1",
            "type": "verse",
            "label": "Couplet",
            "is_instrumental": False,
            "repeats": 1,
            "lines": [
                {
                    "lyrics": "Hello world",
                    "chords": [
                        {"chord": "Am", "position": 0},
                        {"chord": "C", "position": 6},
                    ],
                }
            ],
        },
    ],
}

INVALID_SONG: dict = {
    "meta": {"title": "", "artist": "", "slug": "bad slug with spaces"},
    "chords_used": [],
    "structure_sequence": [],
    "sections": [],
}


def _write_test_song():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"song_{TEST_SLUG}.json"
    path.write_text(json.dumps(VALID_SONG, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _cleanup():
    (DATA_DIR / f"song_{TEST_SLUG}.json").unlink(missing_ok=True)
    for f in OUTPUT_DIR.glob(f"song_{TEST_SLUG}.*"):
        f.unlink(missing_ok=True)
    import shutil
    backup_dir = BACKUP_DIR / TEST_SLUG
    if backup_dir.exists():
        shutil.rmtree(backup_dir)


@pytest.fixture(autouse=True)
def cleanup_around_test():
    _cleanup()
    yield
    _cleanup()


@pytest.fixture
def client():
    flask_app.app.config["TESTING"] = True
    with flask_app.app.test_client() as c:
        yield c


@pytest.fixture
def with_song():
    return _write_test_song()


# ---------------------------------------------------------------------------
# Tests — upload
# ---------------------------------------------------------------------------

class TestUpload:
    def test_upload_json_valide(self, client):
        """Un JSON valide uploadé crée le morceau et redirige vers la fiche."""
        from io import BytesIO
        raw = json.dumps(VALID_SONG).encode("utf-8")
        with patch("app._generate_outputs", return_value={"docx": None, "pdf": None, "pdf_error": None}):
            resp = client.post(
                "/upload",
                data={"json_file": (BytesIO(raw), f"song_{TEST_SLUG}.json")},
            )
        assert resp.status_code in (200, 302)
        assert (DATA_DIR / f"song_{TEST_SLUG}.json").exists()

    def test_upload_json_invalide(self, client):
        """Un JSON invalide (sections vides, slug invalide) est rejeté avec des erreurs."""
        from io import BytesIO
        raw = json.dumps(INVALID_SONG).encode("utf-8")
        resp = client.post(
            "/upload",
            data={"json_file": (BytesIO(raw), "invalid.json")},
        )
        assert resp.status_code == 200
        body = resp.data.decode("utf-8")
        # L'interface doit afficher une erreur de validation
        assert "erreur" in body.lower() or "invalid" in body.lower() or "requis" in body.lower()

    def test_upload_json_malformed(self, client):
        """Un fichier non JSON est rejeté."""
        from io import BytesIO
        resp = client.post(
            "/upload",
            data={"json_file": (BytesIO(b"not json at all"), "bad.json")},
        )
        assert resp.status_code == 200
        body = resp.data.decode("utf-8")
        assert "invalide" in body.lower() or "json" in body.lower()


# ---------------------------------------------------------------------------
# Tests — bibliothèque
# ---------------------------------------------------------------------------

class TestLibrairie:
    def test_route_bibliotheque(self, client, with_song):
        """La route /library retourne 200 et liste les morceaux."""
        resp = client.get("/library")
        assert resp.status_code == 200
        body = resp.data.decode("utf-8")
        assert "Test Song P9" in body
        assert "Test Artist" in body

    def test_route_bibliotheque_vide(self, client):
        """La bibliothèque fonctionne même sans aucun morceau."""
        resp = client.get("/library")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Tests — export JSON
# ---------------------------------------------------------------------------

class TestDownloadJson:
    def test_export_json_existant(self, client, with_song):
        """Télécharger le JSON d'un morceau existant retourne le fichier."""
        resp = client.get(f"/song/{TEST_SLUG}/download-json")
        assert resp.status_code == 200
        assert resp.content_type in ("application/json", "application/octet-stream",
                                     "application/json; charset=utf-8")
        data = json.loads(resp.data)
        assert data["meta"]["slug"] == TEST_SLUG

    def test_export_json_introuvable(self, client):
        """Télécharger un JSON inexistant retourne 404."""
        resp = client.get("/song/slug-inexistant-xyz/download-json")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tests — backup et restauration
# ---------------------------------------------------------------------------

class TestBackup:
    def test_sauvegarde_cree_backup(self, client, with_song):
        """Toute sauvegarde via AJAX crée un backup dans data/backups/<slug>/."""
        from backup import list_backups
        # Déclencher une sauvegarde via la route save-all
        resp = client.post(
            f"/song/{TEST_SLUG}/save-all",
            data={"new_sequence": json.dumps(["intro_1", "verse_1"])},
        )
        assert resp.status_code == 200
        backups = list_backups(TEST_SLUG)
        assert len(backups) >= 1

    def test_restore_backup(self, client, with_song):
        """Restaurer un backup valide redirige avec succès."""
        from backup import list_backups, create_backup
        song_path = DATA_DIR / f"song_{TEST_SLUG}.json"
        create_backup(song_path)
        backups = list_backups(TEST_SLUG)
        assert backups, "Aucun backup créé"
        filename = backups[0]["filename"]
        with patch("app._generate_outputs", return_value={"docx": None, "pdf": None, "pdf_error": None}):
            resp = client.post(f"/song/{TEST_SLUG}/restore/{filename}")
        assert resp.status_code in (200, 302)

    def test_restore_backup_inexistant(self, client, with_song):
        """Restaurer un backup inexistant redirige avec un message d'erreur."""
        resp = client.post(f"/song/{TEST_SLUG}/restore/fichier-inexistant.json")
        assert resp.status_code in (302, 404)


# ---------------------------------------------------------------------------
# Tests — génération split PDF
# ---------------------------------------------------------------------------

class TestExportSplit:
    def test_export_split_redirige(self, client, with_song):
        """L'export split redirige vers la fiche chanson."""
        with patch("app.generate_split_pdf"), \
             patch("app._generate_outputs", return_value={"docx": None, "pdf": None, "pdf_error": None}):
            resp = client.post(f"/song/{TEST_SLUG}/export-split")
        assert resp.status_code in (200, 302)


# ---------------------------------------------------------------------------
# Tests — suppression d'accord (section paroles)
# ---------------------------------------------------------------------------

class TestSuppressionAccord:
    def test_supprimer_accord_valide(self, client, with_song):
        """Supprimer un accord existant retourne ok=True."""
        resp = client.post(
            f"/song/{TEST_SLUG}/chord-at/delete",
            data={"section_id": "verse_1", "line_index": "0", "chord_index": "0"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get("ok") is True

    def test_supprimer_accord_section_inexistante(self, client, with_song):
        """Supprimer un accord sur une section inexistante ne plante pas."""
        resp = client.post(
            f"/song/{TEST_SLUG}/chord-at/delete",
            data={"section_id": "section-inexistante", "line_index": "0", "chord_index": "0"},
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Tests — insertion accord instrumental
# ---------------------------------------------------------------------------

class TestInsertionInstrumentale:
    def test_inserer_accord_instrumental(self, client, with_song):
        """Insérer un accord dans performance_progression retourne ok=True."""
        resp = client.post(
            f"/song/{TEST_SLUG}/instr-chord/insert",
            data={
                "section_id": "intro_1",
                "instr_type": "pp",
                "insert_at": "1",
                "chord": "Em",
                "ppi": "0",
                "li": "0",
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get("ok") is True
        # Vérifier que l'accord est bien inséré dans le JSON
        song = json.loads((DATA_DIR / f"song_{TEST_SLUG}.json").read_text(encoding="utf-8"))
        intro = next(s for s in song["sections"] if s["id"] == "intro_1")
        tokens = intro["performance_progression"][0]["chords"].split()
        assert "Em" in tokens

    def test_inserer_accord_instrumental_manquant(self, client, with_song):
        """Insérer sans accord retourne une erreur 400."""
        resp = client.post(
            f"/song/{TEST_SLUG}/instr-chord/insert",
            data={
                "section_id": "intro_1",
                "instr_type": "pp",
                "insert_at": "0",
                "chord": "",
                "ppi": "0",
                "li": "0",
            },
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Tests — mode répétition (P10)
# ---------------------------------------------------------------------------

class TestRepetition:
    def test_rehearsal_chords_existant(self, client, with_song):
        """La route rehearsal/chords retourne 200 pour un morceau existant."""
        resp = client.get(f"/song/{TEST_SLUG}/rehearsal/chords")
        assert resp.status_code == 200
        body = resp.data.decode("utf-8")
        assert "Test Song P9" in body

    def test_rehearsal_chords_introuvable(self, client):
        """La route rehearsal/chords retourne 404 pour un slug inexistant."""
        resp = client.get("/song/slug-inexistant-xyz/rehearsal/chords")
        assert resp.status_code == 404

    def test_rehearsal_memo_existant(self, client, with_song):
        """La route rehearsal/memo retourne 200 et contient le titre."""
        resp = client.get(f"/song/{TEST_SLUG}/rehearsal/memo")
        assert resp.status_code == 200
        body = resp.data.decode("utf-8")
        assert "Test Song P9" in body

    def test_rehearsal_memo_introuvable(self, client):
        """La route rehearsal/memo retourne 404 pour un slug inexistant."""
        resp = client.get("/song/slug-inexistant-xyz/rehearsal/memo")
        assert resp.status_code == 404

    def test_rehearsal_chords_contient_sections(self, client, with_song):
        """La vue répétition contient les labels de section."""
        resp = client.get(f"/song/{TEST_SLUG}/rehearsal/chords")
        body = resp.data.decode("utf-8")
        assert "Couplet" in body or "Intro" in body


# ---------------------------------------------------------------------------
# Tests — statut de révision (P10)
# ---------------------------------------------------------------------------

class TestReviewStatus:
    def test_update_review_status_ok(self, client, with_song):
        """Mettre le statut 'ok' met à jour le JSON."""
        resp = client.post(
            f"/song/{TEST_SLUG}/review-status",
            data={"status": "ok"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get("ok") is True
        song = json.loads((DATA_DIR / f"song_{TEST_SLUG}.json").read_text(encoding="utf-8"))
        assert song.get("review_status") == "ok"

    def test_update_review_status_to_review(self, client, with_song):
        """Le statut 'to_review' est accepté."""
        resp = client.post(
            f"/song/{TEST_SLUG}/review-status",
            data={"status": "to_review"},
        )
        assert resp.status_code == 200
        assert resp.get_json().get("ok") is True

    def test_update_review_status_invalide(self, client, with_song):
        """Un statut inconnu retourne 400."""
        resp = client.post(
            f"/song/{TEST_SLUG}/review-status",
            data={"status": "invalid"},
        )
        assert resp.status_code == 400

    def test_update_review_status_introuvable(self, client):
        """Mettre à jour sur un slug inexistant retourne 404."""
        resp = client.post(
            "/song/slug-inexistant-xyz/review-status",
            data={"status": "ok"},
        )
        assert resp.status_code == 404

    def test_review_status_vide_supprime_champ(self, client, with_song):
        """Un statut vide supprime le champ review_status."""
        # D'abord, mettre un statut
        client.post(f"/song/{TEST_SLUG}/review-status", data={"status": "ok"})
        # Puis le vider
        resp = client.post(f"/song/{TEST_SLUG}/review-status", data={"status": ""})
        assert resp.status_code == 200
        song = json.loads((DATA_DIR / f"song_{TEST_SLUG}.json").read_text(encoding="utf-8"))
        assert "review_status" not in song


# ---------------------------------------------------------------------------
# Tests — route transposition Flask (P10)
# ---------------------------------------------------------------------------

class TestTransposeRoute:
    def test_transpose_valide(self, client, with_song):
        """La route transpose applique la transposition et retourne ok=True."""
        resp = client.post(
            f"/song/{TEST_SLUG}/transpose",
            data={"semitones": "2"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get("ok") is True

    def test_transpose_zero_rejete(self, client, with_song):
        """0 demi-ton est rejeté (400)."""
        resp = client.post(
            f"/song/{TEST_SLUG}/transpose",
            data={"semitones": "0"},
        )
        assert resp.status_code == 400

    def test_transpose_hors_limites(self, client, with_song):
        """Une valeur hors de −11..+11 est rejetée (400)."""
        resp = client.post(
            f"/song/{TEST_SLUG}/transpose",
            data={"semitones": "15"},
        )
        assert resp.status_code == 400

    def test_transpose_introuvable(self, client):
        """Transposer un slug inexistant retourne 404."""
        resp = client.post(
            "/song/slug-inexistant-xyz/transpose",
            data={"semitones": "1"},
        )
        assert resp.status_code == 404
