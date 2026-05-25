-- Chords — Schéma Supabase
-- À exécuter dans l'éditeur SQL de votre projet Supabase.
--
-- Tables : songs, song_backups
-- Storage bucket : chords-exports
-- ---------------------------------------------------------------------------

-- ---------------------------------------------------------------------------
-- Table : songs
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS songs (
    id                uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    slug              text        UNIQUE NOT NULL,
    title             text        NOT NULL,
    artist            text        NOT NULL,
    album             text,
    key               text,
    capo              integer     DEFAULT 0,
    tempo             integer     DEFAULT 0,
    review_status     text,
    validation_status text        DEFAULT 'pending',
    has_pdf_chords    boolean     DEFAULT false,
    has_pdf_memo      boolean     DEFAULT false,
    song_json         jsonb       NOT NULL,
    created_at        timestamptz DEFAULT now(),
    updated_at        timestamptz DEFAULT now()
);

-- Index sur slug (clé de recherche principale)
CREATE INDEX IF NOT EXISTS idx_songs_slug ON songs (slug);

-- Trigger : met à jour updated_at automatiquement
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS songs_updated_at ON songs;
CREATE TRIGGER songs_updated_at
    BEFORE UPDATE ON songs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- ---------------------------------------------------------------------------
-- Table : song_backups
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS song_backups (
    id        uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    song_id   uuid        REFERENCES songs(id) ON DELETE CASCADE,
    slug      text        NOT NULL,
    song_json jsonb       NOT NULL,
    reason    text        DEFAULT 'auto',
    created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_song_backups_slug    ON song_backups (slug);
CREATE INDEX IF NOT EXISTS idx_song_backups_song_id ON song_backups (song_id);
CREATE INDEX IF NOT EXISTS idx_song_backups_created ON song_backups (slug, created_at DESC);

-- ---------------------------------------------------------------------------
-- Row Level Security (désactivée pour service_role_key côté serveur)
-- ---------------------------------------------------------------------------
-- RLS est désactivée : l'accès se fait uniquement depuis le backend
-- avec SUPABASE_SERVICE_ROLE_KEY, qui bypass RLS.
ALTER TABLE songs        DISABLE ROW LEVEL SECURITY;
ALTER TABLE song_backups DISABLE ROW LEVEL SECURITY;

-- ---------------------------------------------------------------------------
-- Storage bucket : chords-exports
-- À créer manuellement dans Supabase > Storage > New bucket
-- ---------------------------------------------------------------------------
-- Nom    : chords-exports
-- Public : true (pour les URLs publiques PDF)
-- Structure : chords-exports/<slug>/<filename>.pdf
--
-- Exemple d'insertion via SQL (optionnel, préférer l'UI Supabase) :
-- INSERT INTO storage.buckets (id, name, public)
-- VALUES ('chords-exports', 'chords-exports', true)
-- ON CONFLICT (id) DO NOTHING;
