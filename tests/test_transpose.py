"""Tests pour scripts/transpose.py."""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from transpose import transpose_chord, transpose_song


# ---------------------------------------------------------------------------
# transpose_chord — notes naturelles
# ---------------------------------------------------------------------------

class TestTransposeChordNaturals:
    def test_c_plus1(self):
        assert transpose_chord("C", 1) == "C#"

    def test_c_plus2(self):
        assert transpose_chord("C", 2) == "D"

    def test_e_plus1(self):
        assert transpose_chord("E", 1) == "F"

    def test_b_plus1_wraps(self):
        assert transpose_chord("B", 1) == "C"

    def test_c_minus1_wraps(self):
        assert transpose_chord("C", -1) == "B"

    def test_g_minus2(self):
        assert transpose_chord("G", -2) == "F"

    def test_zero_semitones(self):
        assert transpose_chord("Am", 0) == "Am"


# ---------------------------------------------------------------------------
# transpose_chord — accidentels
# ---------------------------------------------------------------------------

class TestTransposeChordAccidentals:
    def test_sharp_up(self):
        assert transpose_chord("C#", 1) == "D"

    def test_flat_up(self):
        assert transpose_chord("Bb", 1) == "B"

    def test_flat_down(self):
        assert transpose_chord("Eb", -1) == "D"

    def test_ab_up(self):
        assert transpose_chord("Ab", 1) == "A"

    def test_enharmonic_db_same_as_csharp(self):
        assert transpose_chord("Db", 1) == transpose_chord("C#", 1)

    def test_enharmonic_gb_same_as_fsharp(self):
        assert transpose_chord("Gb", 2) == transpose_chord("F#", 2)


# ---------------------------------------------------------------------------
# transpose_chord — suffixes
# ---------------------------------------------------------------------------

class TestTransposeChordSuffixes:
    def test_minor(self):
        assert transpose_chord("Am", 2) == "Bm"

    def test_maj7(self):
        assert transpose_chord("Cmaj7", 1) == "C#maj7"

    def test_sus4(self):
        assert transpose_chord("Gsus4", 2) == "Asus4"

    def test_dim(self):
        assert transpose_chord("Bdim", 1) == "Cdim"

    def test_7(self):
        assert transpose_chord("G7", -1) == "F#7"

    def test_minor_7(self):
        assert transpose_chord("Dm7", 3) == "Fm7"


# ---------------------------------------------------------------------------
# transpose_chord — accords de basse (slash chords)
# ---------------------------------------------------------------------------

class TestTransposeSlashChords:
    def test_g_over_b(self):
        assert transpose_chord("G/B", 2) == "A/C#"

    def test_d_over_fsharp(self):
        assert transpose_chord("D/F#", 1) == "Eb/G"

    def test_c_over_e(self):
        assert transpose_chord("C/E", -1) == "B/Eb"


# ---------------------------------------------------------------------------
# transpose_chord — tokens inconnus (pass-through)
# ---------------------------------------------------------------------------

class TestTransposePassThrough:
    def test_nc(self):
        assert transpose_chord("N.C.", 2) == "N.C."

    def test_dash(self):
        assert transpose_chord("-", 1) == "-"

    def test_empty(self):
        assert transpose_chord("", 5) == ""

    def test_number(self):
        assert transpose_chord("4", 3) == "4"


# ---------------------------------------------------------------------------
# transpose_song
# ---------------------------------------------------------------------------

def _make_song(key="Am", chords_used=None, sections=None):
    return {
        "meta": {"title": "T", "artist": "A", "slug": "t", "key": key, "key_mode": "minor"},
        "chords_used": chords_used or ["Am", "C", "G", "F"],
        "structure_sequence": ["verse_1"],
        "sections": sections or [
            {
                "id": "verse_1",
                "type": "verse",
                "label": "Couplet",
                "lines": [
                    {"lyrics": "Hello world", "chords": [{"chord": "Am", "position": 0}, {"chord": "C", "position": 6}]},
                    {"lyrics": "Goodbye", "chords": [{"chord": "G", "position": 0}]},
                ],
            }
        ],
    }


class TestTransposeSong:
    def test_meta_key_updated(self):
        song = _make_song(key="Am")
        result = transpose_song(song, 2)
        assert result["meta"]["key"] == "Bm"

    def test_chords_used_updated(self):
        song = _make_song(chords_used=["Am", "C", "G", "F"])
        result = transpose_song(song, 2)
        assert result["chords_used"] == ["Bm", "D", "A", "G"]

    def test_lines_chords_updated(self):
        song = _make_song()
        result = transpose_song(song, 2)
        line_chords = result["sections"][0]["lines"][0]["chords"]
        assert line_chords[0]["chord"] == "Bm"
        assert line_chords[1]["chord"] == "D"

    def test_chord_grid_updated(self):
        song = _make_song(sections=[{
            "id": "verse_1", "type": "verse", "label": "V",
            "chord_grid": "| Am | C | G | F |",
            "lines": [],
        }])
        result = transpose_song(song, 2)
        assert result["sections"][0]["chord_grid"] == "| Bm | D | A | G |"

    def test_summary_progression_updated(self):
        song = _make_song(sections=[{
            "id": "verse_1", "type": "verse", "label": "V",
            "summary_progression": "Am C G F",
            "lines": [],
        }])
        result = transpose_song(song, 2)
        assert result["sections"][0]["summary_progression"] == "Bm D A G"

    def test_performance_progression_updated(self):
        song = _make_song(sections=[{
            "id": "verse_1", "type": "verse", "label": "V",
            "performance_progression": [{"chords": "Am C G F", "repeat": 2}],
            "lines": [],
        }])
        result = transpose_song(song, 2)
        assert result["sections"][0]["performance_progression"][0]["chords"] == "Bm D A G"

    def test_zero_semitones_no_change(self):
        song = _make_song()
        result = transpose_song(song, 0)
        assert result["chords_used"] == song["chords_used"]

    def test_does_not_mutate_original(self):
        song = _make_song()
        original_key = song["meta"]["key"]
        transpose_song(song, 3)
        assert song["meta"]["key"] == original_key

    def test_round_trip(self):
        song = _make_song(key="C", chords_used=["C", "Am", "F", "G"])
        result = transpose_song(transpose_song(song, 5), -5)
        assert result["chords_used"] == song["chords_used"]
        assert result["meta"]["key"] == song["meta"]["key"]
