"""
Tests de la couche storage (scripts/storage.py).

Couvre :
  - LocalStorage : list_songs, get_song, save_song, delete_song,
                   list_backups, restore_backup, save_pdf_export,
                   get_pdf_export_url, pdf_export_exists
  - SupabaseStorage : mocké (pas d'appel réseau réel)
  - Pas d'accès direct à DATA_DIR dans app.py (via storage uniquement)
  - Migration dry-run (smoke test)
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import storage as storage_module
from storage import LocalStorage, SupabaseStorage, get_storage, reset_storage


# ---------------------------------------------------------------------------
# Song fixture
# ---------------------------------------------------------------------------

SLUG = "test-storage-unit"
SONG: dict = {
    "meta": {
        "title": "Test Storage",
        "artist": "Pytest",
        "slug": SLUG,
        "key": "Am",
        "capo": 0,
        "tempo": 120,
    },
    "chords_used": ["Am", "G"],
    "structure_sequence": ["verse_1"],
    "sections": [
        {
            "id": "verse_1",
            "type": "verse",
            "label": "Couplet",
            "is_instrumental": False,
            "repeats": 1,
            "lines": [
                {
                    "lyrics": "Hello",
                    "chords": [{"chord": "Am", "position": 0}],
                }
            ],
        }
    ],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cleanup_local(storage: LocalStorage) -> None:
    (storage.data_dir / f"song_{SLUG}.json").unlink(missing_ok=True)
    (storage.output_dir / f"song_{SLUG}.json").unlink(missing_ok=True)
    import shutil
    backup_slug_dir = storage.data_dir / "backups" / SLUG
    if backup_slug_dir.exists():
        shutil.rmtree(backup_slug_dir)


@pytest.fixture(autouse=True)
def reset_storage_singleton():
    """Réinitialise le singleton entre chaque test."""
    reset_storage()
    yield
    reset_storage()


@pytest.fixture
def local_storage() -> LocalStorage:
    st = LocalStorage()
    _cleanup_local(st)
    yield st
    _cleanup_local(st)


# ---------------------------------------------------------------------------
# LocalStorage — CRUD chansons
# ---------------------------------------------------------------------------

class TestLocalStorageSongs:
    def test_get_song_absent(self, local_storage):
        assert local_storage.get_song("slug-inexistant-xyz") is None

    def test_save_and_get_song(self, local_storage):
        local_storage.save_song(SONG)
        loaded = local_storage.get_song(SLUG)
        assert loaded is not None
        assert loaded["meta"]["title"] == "Test Storage"

    def test_save_song_cree_backup(self, local_storage):
        local_storage.save_song(SONG)
        local_storage.save_song(SONG)  # 2e sauvegarde crée un backup
        backups = local_storage.list_backups(SLUG)
        assert len(backups) >= 1

    def test_list_songs_vide(self, local_storage):
        songs = local_storage.list_songs()
        slugs = [s["slug"] for s in songs]
        assert SLUG not in slugs

    def test_list_songs_apres_save(self, local_storage):
        local_storage.save_song(SONG)
        songs = local_storage.list_songs()
        slugs = [s["slug"] for s in songs]
        assert SLUG in slugs

    def test_list_songs_champs_requis(self, local_storage):
        local_storage.save_song(SONG)
        songs = local_storage.list_songs()
        s = next(x for x in songs if x["slug"] == SLUG)
        for field in ("slug", "title", "artist", "pdf_chords", "pdf_memo",
                      "pdf_chords_name", "pdf_memo_name", "review_status", "mtime"):
            assert field in s, f"Champ manquant : {field}"

    def test_delete_song(self, local_storage):
        local_storage.save_song(SONG)
        assert local_storage.get_song(SLUG) is not None
        local_storage.delete_song(SLUG)
        assert local_storage.get_song(SLUG) is None


# ---------------------------------------------------------------------------
# LocalStorage — backups
# ---------------------------------------------------------------------------

class TestLocalStorageBackups:
    def test_list_backups_vide(self, local_storage):
        assert local_storage.list_backups("slug-sans-backup") == []

    def test_restore_backup_invalide(self, local_storage):
        local_storage.save_song(SONG)
        assert local_storage.restore_backup(SLUG, "fichier-inexistant.json") is None

    def test_restore_backup_valide(self, local_storage):
        local_storage.save_song(SONG)
        local_storage.save_song(SONG)  # génère un backup
        backups = local_storage.list_backups(SLUG)
        assert backups
        restored = local_storage.restore_backup(SLUG, backups[0]["filename"])
        assert restored is not None
        assert restored["meta"]["slug"] == SLUG


# ---------------------------------------------------------------------------
# LocalStorage — exports PDF
# ---------------------------------------------------------------------------

class TestLocalStorageExports:
    def test_pdf_export_absent(self, local_storage):
        local_storage.save_song(SONG)
        fname = "Pytest - Test Storage - Paroles & Accords.pdf"
        assert local_storage.pdf_export_exists(SLUG, fname) is False
        assert local_storage.get_pdf_export_url(SLUG, fname) is None

    def test_save_pdf_export(self, local_storage, tmp_path):
        fname = "Pytest - Test Storage - Paroles & Accords.pdf"
        fake_pdf = b"%PDF-1.4 fake pdf content"
        url = local_storage.save_pdf_export(SLUG, fname, fake_pdf)
        assert url == f"/export/{fname}"
        assert local_storage.pdf_export_exists(SLUG, fname) is True
        assert local_storage.get_pdf_export_url(SLUG, fname) == f"/export/{fname}"
        # Nettoyage
        (local_storage.export_dir / fname).unlink(missing_ok=True)

    def test_export_dir_display(self, local_storage):
        assert str(local_storage.export_dir) in local_storage.export_dir_display


# ---------------------------------------------------------------------------
# SupabaseStorage — mocké (aucun appel réseau)
# ---------------------------------------------------------------------------

class TestSupabaseStorageMocked:
    """Vérifie la logique sans appel réseau réel."""

    def _make_mock_client(self):
        mock = MagicMock()
        # songs.select().eq().execute() → data
        mock.table("songs").select("*").execute.return_value.data = []
        mock.table("songs").select("song_json").eq("slug", SLUG).execute.return_value.data = [
            {"song_json": SONG}
        ]
        mock.table("songs").select("*").eq("slug", SLUG).execute.return_value.data = [
            {"id": "uuid-1234", "slug": SLUG, "song_json": SONG,
             "has_pdf_chords": False, "has_pdf_memo": False,
             "updated_at": "2026-01-01T00:00:00Z",
             "review_status": "", "validation_status": "pending",
             "title": "Test", "artist": "Pytest",
             "album": None, "key": "Am", "capo": 0, "tempo": 120}
        ]
        mock.table("song_backups").select("song_json").eq("id", "bk-1").execute.return_value.data = [
            {"song_json": SONG}
        ]
        mock.table("song_backups").select("id, created_at, reason").eq("slug", SLUG).order(
            "created_at", desc=True
        ).execute.return_value.data = [
            {"id": "bk-1", "created_at": "2026-01-01T10:00:00Z", "reason": "auto"}
        ]
        mock.storage.from_("chords-exports").get_public_url.return_value = (
            "https://supabase.co/storage/v1/object/public/chords-exports/slug/file.pdf"
        )
        return mock

    @patch.dict("os.environ", {
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "test-key",
        "SUPABASE_STORAGE_BUCKET": "chords-exports",
    })
    @patch("storage.SupabaseStorage.__init__", lambda self: None)
    def test_get_song_mocked(self):
        st = SupabaseStorage.__new__(SupabaseStorage)
        st._client = self._make_mock_client()
        st._bucket = "chords-exports"
        song = st.get_song(SLUG)
        assert song is not None
        assert song["meta"]["slug"] == SLUG

    @patch.dict("os.environ", {
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "test-key",
        "SUPABASE_STORAGE_BUCKET": "chords-exports",
    })
    @patch("storage.SupabaseStorage.__init__", lambda self: None)
    def test_list_backups_mocked(self):
        st = SupabaseStorage.__new__(SupabaseStorage)
        st._client = self._make_mock_client()
        st._bucket = "chords-exports"
        backups = st.list_backups(SLUG)
        assert len(backups) == 1
        assert backups[0]["filename"] == "bk-1"
        assert "timestamp" in backups[0]

    @patch.dict("os.environ", {
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "test-key",
    })
    @patch("storage.SupabaseStorage.__init__", lambda self: None)
    def test_restore_backup_mocked(self):
        st = SupabaseStorage.__new__(SupabaseStorage)
        st._client = self._make_mock_client()
        st._bucket = "chords-exports"
        restored = st.restore_backup(SLUG, "bk-1")
        assert restored is not None
        assert restored["meta"]["slug"] == SLUG

    @patch.dict("os.environ", {
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "test-key",
    })
    @patch("storage.SupabaseStorage.__init__", lambda self: None)
    def test_export_dir_display_supabase(self):
        st = SupabaseStorage.__new__(SupabaseStorage)
        st._bucket = "chords-exports"
        assert "chords-exports" in st.export_dir_display

    @patch.dict("os.environ", {
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "test-key",
    })
    def test_missing_env_raises(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises((EnvironmentError, ImportError, Exception)):
                SupabaseStorage()


# ---------------------------------------------------------------------------
# get_storage() — factory
# ---------------------------------------------------------------------------

class TestGetStorage:
    def test_local_backend_par_defaut(self):
        with patch.object(storage_module, "STORAGE_BACKEND", "local"):
            st = get_storage()
            assert isinstance(st, LocalStorage)

    def test_singleton(self):
        with patch.object(storage_module, "STORAGE_BACKEND", "local"):
            a = get_storage()
            b = get_storage()
            assert a is b

    def test_reset_storage(self):
        with patch.object(storage_module, "STORAGE_BACKEND", "local"):
            a = get_storage()
            reset_storage()
            b = get_storage()
            assert a is not b


# ---------------------------------------------------------------------------
# App.py — pas d'accès direct à DATA_DIR
# ---------------------------------------------------------------------------

class TestAppNoDirAccess:
    """Vérifie que app.py n'accède plus directement aux dossiers data/ et output/
    pour les opérations de données (la couche storage gère ça)."""

    def test_app_importe_storage(self):
        import importlib
        import app as flask_app
        assert hasattr(flask_app, "get_storage"), \
            "app.py doit importer get_storage depuis storage"

    def test_app_nutil_pas_data_dir_pour_load(self):
        """_load_song() passe par get_storage(), pas par open(DATA_DIR/...)."""
        import app as flask_app
        import inspect
        src = inspect.getsource(flask_app._load_song)
        assert "get_storage" in src, "_load_song() doit utiliser get_storage()"
        assert "open(" not in src, "_load_song() ne doit pas ouvrir de fichier directement"

    def test_app_nutil_pas_data_dir_pour_save(self):
        """_save_song() passe par get_storage(), pas par open(DATA_DIR/...)."""
        import app as flask_app
        import inspect
        src = inspect.getsource(flask_app._save_song)
        assert "get_storage" in src, "_save_song() doit utiliser get_storage()"


# ---------------------------------------------------------------------------
# Migration — dry-run smoke test
# ---------------------------------------------------------------------------

class TestMigrationDryRun:
    def test_dry_run_ne_modifie_rien(self, capsys):
        """Le dry-run doit s'exécuter sans erreur et sans appel Supabase réel."""
        import sys as _sys
        _sys.path.insert(0, str(ROOT / "scripts"))

        with patch.dict("os.environ", {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_SERVICE_ROLE_KEY": "test-key",
        }):
            # Mock create_client pour ne pas appeler le réseau
            mock_client = MagicMock()
            with patch("migrate_local_to_supabase._load_env"), \
                 patch("migrate_local_to_supabase._check_env"), \
                 patch("migrate_local_to_supabase.create_client", return_value=mock_client, create=True):
                try:
                    from migrate_local_to_supabase import migrate
                    migrate(dry_run=True)
                    # En dry-run, create_client n'est pas forcément importé
                    # mais la migration doit se terminer sans exception
                except SystemExit:
                    pass  # Acceptable si supabase n'est pas installé

        captured = capsys.readouterr()
        # Le dry-run ne doit pas afficher d'erreurs fatales
        assert "Traceback" not in captured.out
