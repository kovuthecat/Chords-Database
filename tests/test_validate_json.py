"""
Tests unitaires pour scripts/validate_song_json.py
Couvre : champs obligatoires, cohérence structure_sequence/sections, positions d'accords.
"""
import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from validate_song_json import validate_song_json


# ---------------------------------------------------------------------------
# Fixture — JSON valide minimal
# ---------------------------------------------------------------------------

def _make_valid_song(**overrides) -> dict:
    song = {
        "meta": {
            "title": "Test Song",
            "artist": "Test Artist",
            "slug": "test-artist-test-song",
            "capo": 0,
        },
        "chords_used": ["Am", "C", "G", "F"],
        "structure_sequence": ["intro_1", "verse_1"],
        "sections": [
            {
                "id": "intro_1",
                "type": "intro",
                "label": "Intro",
                "is_instrumental": True,
                "chord_grid": "| Am | C | G | F |",
                "repeats": 1,
            },
            {
                "id": "verse_1",
                "type": "verse",
                "label": "Couplet",
                "is_instrumental": False,
                "lines": [
                    {
                        "lyrics": "Première ligne",
                        "chords": [{"chord": "Am", "position": 0}, {"chord": "C", "position": 10}],
                    }
                ],
            },
        ],
        "validation": {"status": "pending", "validated_at": None, "user_corrections": []},
        "confidence": {"overall": 0.8},
    }
    song.update(overrides)
    return song


# ---------------------------------------------------------------------------
# JSON valide
# ---------------------------------------------------------------------------

class TestValidJSON:
    def test_json_valide_retourne_liste_vide(self):
        errors = validate_song_json(_make_valid_song())
        assert errors == []

    def test_json_avec_performance_progression_valide(self):
        song = _make_valid_song()
        song["sections"][0]["performance_progression"] = [{"chords": "Am C G F", "repeat": 2}]
        assert validate_song_json(song) == []

    def test_json_sans_chords_used_mais_chord_grid(self):
        song = _make_valid_song()
        song["chords_used"] = []
        # sections[0] a un chord_grid → doit être valide
        assert validate_song_json(song) == []


# ---------------------------------------------------------------------------
# Champs meta obligatoires
# ---------------------------------------------------------------------------

class TestMetaRequired:
    def test_meta_manquant(self):
        song = _make_valid_song()
        del song["meta"]
        errors = validate_song_json(song)
        assert any("meta" in e.lower() for e in errors)

    def test_title_manquant(self):
        song = _make_valid_song()
        song["meta"]["title"] = ""
        errors = validate_song_json(song)
        assert any("title" in e for e in errors)

    def test_artist_manquant(self):
        song = _make_valid_song()
        del song["meta"]["artist"]
        errors = validate_song_json(song)
        assert any("artist" in e for e in errors)

    def test_slug_manquant(self):
        song = _make_valid_song()
        song["meta"]["slug"] = ""
        errors = validate_song_json(song)
        assert any("slug" in e for e in errors)


# ---------------------------------------------------------------------------
# Sections obligatoires
# ---------------------------------------------------------------------------

class TestSectionsRequired:
    def test_sections_vides(self):
        song = _make_valid_song()
        song["sections"] = []
        errors = validate_song_json(song)
        assert any("sections" in e.lower() for e in errors)

    def test_sections_manquantes(self):
        song = _make_valid_song()
        del song["sections"]
        errors = validate_song_json(song)
        assert any("sections" in e.lower() for e in errors)

    def test_section_sans_id(self):
        song = _make_valid_song()
        song["sections"][0] = {"type": "intro"}  # sans id
        errors = validate_song_json(song)
        assert any("id" in e for e in errors)


# ---------------------------------------------------------------------------
# structure_sequence
# ---------------------------------------------------------------------------

class TestStructureSequence:
    def test_structure_sequence_vide(self):
        song = _make_valid_song()
        song["structure_sequence"] = []
        errors = validate_song_json(song)
        assert any("structure_sequence" in e for e in errors)

    def test_structure_sequence_id_inexistant(self):
        song = _make_valid_song()
        song["structure_sequence"] = ["intro_1", "verse_1", "chorus_INEXISTANT"]
        errors = validate_song_json(song)
        assert any("chorus_INEXISTANT" in e for e in errors)

    def test_structure_sequence_comment_ignore(self):
        song = _make_valid_song()
        song["structure_sequence"] = ["_comment: intro", "intro_1", "verse_1"]
        assert validate_song_json(song) == []


# ---------------------------------------------------------------------------
# Accords
# ---------------------------------------------------------------------------

class TestChords:
    def test_aucun_accord_nulle_part(self):
        song = _make_valid_song()
        song["chords_used"] = []
        for s in song["sections"]:
            s.pop("chord_grid", None)
            s.pop("summary_progression", None)
            s["lines"] = []
        errors = validate_song_json(song)
        assert any("accord" in e.lower() for e in errors)

    def test_position_accord_non_entier(self):
        song = _make_valid_song()
        song["sections"][1]["lines"][0]["chords"][0]["position"] = "0"  # string au lieu d'int
        errors = validate_song_json(song)
        assert any("position" in e for e in errors)

    def test_position_entier_zero_valide(self):
        song = _make_valid_song()
        song["sections"][1]["lines"][0]["chords"][0]["position"] = 0
        assert validate_song_json(song) == []


# ---------------------------------------------------------------------------
# performance_progression
# ---------------------------------------------------------------------------

class TestPerformanceProgression:
    def test_entry_sans_chords(self):
        song = _make_valid_song()
        song["sections"][0]["performance_progression"] = [{"repeat": 2}]  # sans "chords"
        errors = validate_song_json(song)
        assert any("performance_progression" in e for e in errors)

    def test_entry_non_dict(self):
        song = _make_valid_song()
        song["sections"][0]["performance_progression"] = ["Am C G"]  # string au lieu d'objet
        errors = validate_song_json(song)
        assert any("performance_progression" in e for e in errors)


# ---------------------------------------------------------------------------
# Lecture depuis fichier JSON (template officiel)
# ---------------------------------------------------------------------------

class TestFromFile:
    def test_template_officiel_est_valide(self):
        template_path = Path(__file__).parent.parent / "song_template_with_rhythm.json"
        if not template_path.exists():
            # Fichier absent → skip
            return
        with open(template_path, encoding="utf-8") as f:
            song = json.load(f)
        errors = validate_song_json(song)
        assert errors == [], f"Template non valide : {errors}"

    def test_json_existants_sont_valides(self):
        data_dir = Path(__file__).parent.parent / "data"
        for p in data_dir.glob("song_*.json"):
            with open(p, encoding="utf-8") as f:
                song = json.load(f)
            # Fichiers brouillons (sections vides) : on les ignore
            if not song.get("sections"):
                continue
            errors = validate_song_json(song)
            assert errors == [], f"{p.name} invalide : {errors}"
