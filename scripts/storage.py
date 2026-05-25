"""
Couche de stockage abstraite pour Chords.

Choisir le backend via la variable d'environnement STORAGE_BACKEND :
    STORAGE_BACKEND=local     → fichiers locaux (défaut)
    STORAGE_BACKEND=supabase  → Supabase Postgres + Storage

Usage dans app.py :
    from storage import get_storage
    storage = get_storage()
    song = storage.get_song(slug)
    storage.save_song(song)
"""

import json
import os
from abc import ABC, abstractmethod
from pathlib import Path

STORAGE_BACKEND: str = os.environ.get("STORAGE_BACKEND", "local")


# ---------------------------------------------------------------------------
# Interface commune
# ---------------------------------------------------------------------------

class StorageBackend(ABC):
    """Interface commune aux deux backends."""

    @abstractmethod
    def list_songs(self) -> list[dict]:
        """Liste tous les morceaux avec leurs métadonnées."""

    @abstractmethod
    def get_song(self, slug: str) -> dict | None:
        """Charge le JSON complet d'un morceau. None si introuvable."""

    @abstractmethod
    def save_song(self, song: dict) -> None:
        """Sauvegarde (upsert) un morceau. Crée un backup avant d'écraser."""

    @abstractmethod
    def delete_song(self, slug: str) -> None:
        """Supprime un morceau et ses fichiers associés."""

    @abstractmethod
    def list_backups(self, slug: str) -> list[dict]:
        """Liste les backups d'un morceau (du plus récent au plus ancien).
        Chaque dict contient au moins : filename, timestamp."""

    @abstractmethod
    def restore_backup(self, slug: str, backup_id: str) -> dict | None:
        """Charge un backup. None si introuvable."""

    @abstractmethod
    def save_pdf_export(self, slug: str, filename: str, pdf_bytes: bytes) -> str:
        """Stocke un PDF exporté. Retourne l'URL de téléchargement."""

    @abstractmethod
    def get_pdf_export_url(self, slug: str, filename: str) -> str | None:
        """Retourne l'URL d'un PDF exporté. None si absent."""

    @abstractmethod
    def pdf_export_exists(self, slug: str, filename: str) -> bool:
        """Indique si un PDF exporté existe."""

    @property
    @abstractmethod
    def export_dir_display(self) -> str:
        """Chaîne affichée dans l'UI pour indiquer où vont les PDFs."""


# ---------------------------------------------------------------------------
# Backend local (filesystem)
# ---------------------------------------------------------------------------

class LocalStorage(StorageBackend):
    """Backend fichiers locaux — comportement identique à l'original."""

    def __init__(self) -> None:
        from config import DATA_DIR, OUTPUT_DIR, PDF_EXPORT_DIR
        self.data_dir   = DATA_DIR
        self.output_dir = OUTPUT_DIR
        self.export_dir = PDF_EXPORT_DIR

    # -- helpers internes --

    def _split_pdf_filename(self, song: dict, part: str) -> str:
        from generate_docx import _split_pdf_filename
        return _split_pdf_filename(song, part)

    # -- interface --

    def list_songs(self) -> list[dict]:
        songs = []
        for p in sorted(self.data_dir.glob("song_*.json")):
            try:
                with open(p, encoding="utf-8") as f:
                    s = json.load(f)
                meta = s.get("meta", {})
                slug = meta.get("slug", p.stem.removeprefix("song_"))
                chords_name = self._split_pdf_filename(s, "chords")
                memo_name   = self._split_pdf_filename(s, "memo")
                songs.append({
                    "slug":           slug,
                    "title":          meta.get("title", "?"),
                    "artist":         meta.get("artist", "?"),
                    "album":          meta.get("album", ""),
                    "key":            meta.get("key", ""),
                    "key_mode":       meta.get("key_mode", "major"),
                    "capo":           meta.get("capo", 0),
                    "tempo":          meta.get("tempo", 0),
                    "status":         s.get("validation", {}).get("status", "pending"),
                    "score":          s.get("confidence", {}).get("overall", 0),
                    "docx":           (self.output_dir / f"song_{slug}.docx").exists(),
                    "pdf":            (self.output_dir / f"song_{slug}.pdf").exists(),
                    "pdf_chords":     (self.export_dir / chords_name).exists(),
                    "pdf_memo":       (self.export_dir / memo_name).exists(),
                    "pdf_chords_name": chords_name,
                    "pdf_memo_name":   memo_name,
                    "pdf_chords_url": f"/export/{chords_name}" if (self.export_dir / chords_name).exists() else None,
                    "pdf_memo_url":   f"/export/{memo_name}"   if (self.export_dir / memo_name).exists()   else None,
                    "review_status":  s.get("review_status", ""),
                    "mtime":          p.stat().st_mtime,
                })
            except Exception:
                pass
        return songs

    def get_song(self, slug: str) -> dict | None:
        path = self.data_dir / f"song_{slug}.json"
        if not path.exists():
            return None
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def save_song(self, song: dict) -> None:
        from backup import create_backup
        slug = song["meta"]["slug"]
        self.data_dir.mkdir(parents=True, exist_ok=True)
        song_path = self.data_dir / f"song_{slug}.json"
        create_backup(song_path)
        with open(song_path, "w", encoding="utf-8") as f:
            json.dump(song, f, ensure_ascii=False, indent=2)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        with open(self.output_dir / f"song_{slug}.json", "w", encoding="utf-8") as f:
            json.dump(song, f, ensure_ascii=False, indent=2)

    def delete_song(self, slug: str) -> None:
        song = self.get_song(slug)
        (self.data_dir / f"song_{slug}.json").unlink(missing_ok=True)
        for f in self.output_dir.glob(f"song_{slug}.*"):
            f.unlink(missing_ok=True)
        if song:
            for part in ("chords", "memo"):
                fname = self._split_pdf_filename(song, part)
                (self.export_dir / fname).unlink(missing_ok=True)

    def list_backups(self, slug: str) -> list[dict]:
        from backup import list_backups
        return list_backups(slug)

    def restore_backup(self, slug: str, backup_id: str) -> dict | None:
        from backup import restore_backup
        return restore_backup(slug, backup_id)

    def save_pdf_export(self, slug: str, filename: str, pdf_bytes: bytes) -> str:
        self.export_dir.mkdir(parents=True, exist_ok=True)
        (self.export_dir / filename).write_bytes(pdf_bytes)
        return f"/export/{filename}"

    def get_pdf_export_url(self, slug: str, filename: str) -> str | None:
        if (self.export_dir / filename).exists():
            return f"/export/{filename}"
        return None

    def pdf_export_exists(self, slug: str, filename: str) -> bool:
        return (self.export_dir / filename).exists()

    @property
    def export_dir_display(self) -> str:
        return str(self.export_dir)


# ---------------------------------------------------------------------------
# Backend Supabase
# ---------------------------------------------------------------------------

class SupabaseStorage(StorageBackend):
    """Backend Supabase — Postgres pour les données, Storage pour les PDFs."""

    def __init__(self) -> None:
        try:
            from supabase import create_client
        except ImportError as exc:
            raise ImportError(
                "Le package 'supabase' est requis pour STORAGE_BACKEND=supabase.\n"
                "Installer : pip install supabase"
            ) from exc

        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        if not url or not key:
            raise EnvironmentError(
                "SUPABASE_URL et SUPABASE_SERVICE_ROLE_KEY doivent être définis."
            )

        self._client = create_client(url, key)
        self._bucket = os.environ.get("SUPABASE_STORAGE_BUCKET", "chords-exports")

    # -- helpers internes --

    def _split_pdf_filename(self, song: dict, part: str) -> str:
        meta  = song.get("meta", {})
        artist = meta.get("artist", "")
        title  = meta.get("title", "")
        label  = {"chords": "Paroles & Accords", "memo": "Mémo Guitare"}.get(part, part)

        def sanitize(s: str) -> str:
            for ch in r'\/:*?"<>|':
                s = s.replace(ch, "-")
            return s.strip()

        return f"{sanitize(artist)} - {sanitize(title)} - {label}.pdf"

    def _get_song_row(self, slug: str) -> dict | None:
        resp = self._client.table("songs").select("*").eq("slug", slug).execute()
        return resp.data[0] if resp.data else None

    def _create_backup_internal(self, slug: str, song: dict, reason: str = "auto") -> None:
        row = self._get_song_row(slug)
        if not row:
            return
        self._client.table("song_backups").insert({
            "song_id":   row["id"],
            "slug":      slug,
            "song_json": song,
            "reason":    reason,
        }).execute()

    # -- interface --

    def list_songs(self) -> list[dict]:
        from datetime import datetime, timezone
        resp = self._client.table("songs").select("*").execute()
        songs = []
        for row in resp.data:
            song = row["song_json"]
            meta = song.get("meta", {})
            slug = row["slug"]

            updated = row.get("updated_at", "")
            try:
                mtime = datetime.fromisoformat(
                    updated.replace("Z", "+00:00")
                ).timestamp() if updated else 0.0
            except Exception:
                mtime = 0.0

            chords_name = self._split_pdf_filename(song, "chords")
            memo_name   = self._split_pdf_filename(song, "memo")
            has_chords  = row.get("has_pdf_chords", False)
            has_memo    = row.get("has_pdf_memo", False)

            songs.append({
                "slug":           slug,
                "title":          meta.get("title", "?"),
                "artist":         meta.get("artist", "?"),
                "album":          meta.get("album", ""),
                "key":            meta.get("key", ""),
                "key_mode":       meta.get("key_mode", "major"),
                "capo":           meta.get("capo", 0),
                "tempo":          meta.get("tempo", 0),
                "status":         song.get("validation", {}).get("status", "pending"),
                "score":          song.get("confidence", {}).get("overall", 0),
                "docx":           False,
                "pdf":            False,
                "pdf_chords":     has_chords,
                "pdf_memo":       has_memo,
                "pdf_chords_name": chords_name,
                "pdf_memo_name":   memo_name,
                "pdf_chords_url":  self._public_url(slug, chords_name) if has_chords else None,
                "pdf_memo_url":    self._public_url(slug, memo_name)   if has_memo   else None,
                "review_status":  song.get("review_status", ""),
                "mtime":          mtime,
            })
        return songs

    def get_song(self, slug: str) -> dict | None:
        resp = self._client.table("songs").select("song_json").eq("slug", slug).execute()
        return resp.data[0]["song_json"] if resp.data else None

    def save_song(self, song: dict) -> None:
        slug = song["meta"]["slug"]
        meta = song.get("meta", {})

        # Backup de la version précédente
        existing = self.get_song(slug)
        if existing:
            self._create_backup_internal(slug, existing, "auto")

        self._client.table("songs").upsert({
            "slug":              slug,
            "title":             meta.get("title", ""),
            "artist":            meta.get("artist", ""),
            "album":             meta.get("album"),
            "key":               meta.get("key"),
            "capo":              meta.get("capo", 0),
            "tempo":             meta.get("tempo", 0),
            "review_status":     song.get("review_status", ""),
            "validation_status": song.get("validation", {}).get("status", "pending"),
            "song_json":         song,
        }, on_conflict="slug").execute()

    def delete_song(self, slug: str) -> None:
        self._client.table("songs").delete().eq("slug", slug).execute()
        # Supprime les fichiers Storage du slug
        try:
            files = self._client.storage.from_(self._bucket).list(slug)
            if files:
                paths = [f"{slug}/{f['name']}" for f in files]
                self._client.storage.from_(self._bucket).remove(paths)
        except Exception:
            pass

    def list_backups(self, slug: str) -> list[dict]:
        resp = (
            self._client.table("song_backups")
            .select("id, created_at, reason")
            .eq("slug", slug)
            .order("created_at", desc=True)
            .execute()
        )
        return [
            {
                "filename":  str(row["id"]),          # UUID utilisé comme backup_id
                "timestamp": row["created_at"],
                "size_kb":   0,
                "reason":    row.get("reason", ""),
            }
            for row in resp.data
        ]

    def restore_backup(self, slug: str, backup_id: str) -> dict | None:
        resp = (
            self._client.table("song_backups")
            .select("song_json")
            .eq("id", backup_id)
            .execute()
        )
        return resp.data[0]["song_json"] if resp.data else None

    def _public_url(self, slug: str, filename: str) -> str:
        return self._client.storage.from_(self._bucket).get_public_url(
            f"{slug}/{filename}"
        )

    def save_pdf_export(self, slug: str, filename: str, pdf_bytes: bytes) -> str:
        path = f"{slug}/{filename}"
        self._client.storage.from_(self._bucket).upload(
            path,
            pdf_bytes,
            {"content-type": "application/pdf", "upsert": "true"},
        )
        # Mise à jour des flags has_pdf_*
        name_lower = filename.lower()
        if "paroles" in name_lower or "accords" in name_lower or "chords" in name_lower:
            self._client.table("songs").update({"has_pdf_chords": True}).eq("slug", slug).execute()
        elif "memo" in name_lower or "mémo" in name_lower:
            self._client.table("songs").update({"has_pdf_memo": True}).eq("slug", slug).execute()
        return self._public_url(slug, filename)

    def get_pdf_export_url(self, slug: str, filename: str) -> str | None:
        row = self._get_song_row(slug)
        if not row:
            return None
        name_lower = filename.lower()
        if "paroles" in name_lower or "accords" in name_lower or "chords" in name_lower:
            if row.get("has_pdf_chords"):
                return self._public_url(slug, filename)
        elif "memo" in name_lower or "mémo" in name_lower:
            if row.get("has_pdf_memo"):
                return self._public_url(slug, filename)
        return None

    def pdf_export_exists(self, slug: str, filename: str) -> bool:
        return self.get_pdf_export_url(slug, filename) is not None

    @property
    def export_dir_display(self) -> str:
        return f"Supabase Storage ({self._bucket})"


# ---------------------------------------------------------------------------
# Factory — singleton par processus
# ---------------------------------------------------------------------------

_instance: StorageBackend | None = None


def get_storage() -> StorageBackend:
    """Retourne l'instance de storage (singleton paresseux)."""
    global _instance
    if _instance is None:
        if STORAGE_BACKEND == "supabase":
            _instance = SupabaseStorage()
        else:
            _instance = LocalStorage()
    return _instance


def reset_storage() -> None:
    """Réinitialise le singleton — utile pour les tests."""
    global _instance
    _instance = None
