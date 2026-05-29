"""
Tests pour rhythm_utils et le rendu rythme dans memo.py.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from rhythm_utils import normalize_rhythm_input, load_presets, get_preset_by_id
from memo import _build_rhythm_hint


# ---------------------------------------------------------------------------
# normalize_rhythm_input
# ---------------------------------------------------------------------------

class TestNormalizeRhythmInput:
    def test_d_to_down(self):
        assert normalize_rhythm_input("d") == "↓"

    def test_u_to_up(self):
        assert normalize_rhythm_input("u") == "↑"

    def test_mixed_pattern(self):
        assert normalize_rhythm_input("d du udu") == "↓ ↓↑ ↑↓↑"

    def test_spaces_preserved(self):
        assert normalize_rhythm_input("d u") == "↓ ↑"

    def test_already_unicode_preserved(self):
        assert normalize_rhythm_input("↓ ↑") == "↓ ↑"

    def test_other_chars_preserved(self):
        assert normalize_rhythm_input("p i m a") == "p i m a"

    def test_empty_string(self):
        assert normalize_rhythm_input("") == ""


# ---------------------------------------------------------------------------
# load_presets / get_preset_by_id
# ---------------------------------------------------------------------------

class TestPresets:
    def test_presets_is_list(self):
        presets = load_presets()
        assert isinstance(presets, list)
        assert len(presets) > 0

    def test_preset_has_required_fields(self):
        for p in load_presets():
            assert "id" in p
            assert "label" in p
            assert "pattern" in p
            assert "feel" in p

    def test_get_preset_by_id_found(self):
        p = get_preset_by_id("straight-du")
        assert p is not None
        assert p["label"] == "Straight DU"

    def test_get_preset_by_id_not_found(self):
        p = get_preset_by_id("inexistant-preset-xyz")
        assert p is None


# ---------------------------------------------------------------------------
# _build_rhythm_hint (memo.py)
# ---------------------------------------------------------------------------

def _sec(rhythm=None):
    """Helper : crée une section minimaliste avec le champ rhythm donné."""
    s = {"id": "test", "type": "verse"}
    if rhythm is not None:
        s["rhythm"] = rhythm
    return s


class TestBuildRhythmHint:
    def test_pattern_and_feel(self):
        hint = _build_rhythm_hint(_sec({"pattern": "↓ ↑↑↓↑", "feel": "folk"}))
        assert hint == "↓ ↑↑↓↑ · folk"

    def test_pattern_only(self):
        hint = _build_rhythm_hint(_sec({"pattern": "↓ ↑"}))
        assert hint == "↓ ↑"

    def test_feel_only(self):
        hint = _build_rhythm_hint(_sec({"feel": "swing"}))
        assert hint == "swing"

    def test_no_rhythm(self):
        hint = _build_rhythm_hint(_sec())
        assert hint == ""

    def test_pattern_lines_joined(self):
        hint = _build_rhythm_hint(_sec({
            "pattern": "↓ ↑",
            "pattern_lines": ["↓ ↑", "↓↑ ↓↑"],
            "feel": "straight"
        }))
        assert "↓ ↑ | ↓↑ ↓↑" in hint
        assert "straight" in hint

    def test_pattern_lines_overrides_pattern(self):
        """Si pattern_lines est présent, il est utilisé à la place de pattern."""
        hint = _build_rhythm_hint(_sec({
            "pattern": "OLD",
            "pattern_lines": ["↓ ↑", "↓↑"],
        }))
        assert "OLD" not in hint
        assert "↓ ↑ | ↓↑" in hint

    def test_empty_pattern_lines_falls_back_to_pattern(self):
        hint = _build_rhythm_hint(_sec({
            "pattern": "↓ ↑",
            "pattern_lines": [],
        }))
        assert hint == "↓ ↑"

    def test_rhythm_hint_fallback(self):
        """Sans clé rhythm, utilise rhythm_hint si présent."""
        sec = {"id": "x", "type": "verse", "rhythm_hint": "↓ ↑ · folk"}
        hint = _build_rhythm_hint(sec)
        assert hint == "↓ ↑ · folk"

    def test_validation_after_move_positions_valid(self):
        """Après move_chord_at, les positions restent ordonnées (smoke test intégration)."""
        from editor import move_chord_at
        from validate_song_json import validate_song_json
        song = {
            "meta": {"title": "T", "artist": "A", "slug": "t-a"},
            "chords_used": ["Am", "C"],
            "structure_sequence": ["v1"],
            "sections": [{
                "id": "v1", "type": "verse", "label": "V",
                "lines": [{"lyrics": "hello world", "chords": [
                    {"chord": "Am", "position": 0},
                    {"chord": "C", "position": 6},
                ]}]
            }]
        }
        moved = move_chord_at(song, "v1", 0, 0, 3)
        errors = validate_song_json(moved)
        assert errors == []
