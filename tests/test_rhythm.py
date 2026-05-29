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

    def test_normalize_preserves_slash(self):
        assert normalize_rhythm_input("d / du") == "↓ / ↓↑"

    def test_normalize_preserves_dot(self):
        assert normalize_rhythm_input("d . u") == "↓ . ↑"

    def test_normalize_preserves_x(self):
        assert normalize_rhythm_input("d x u") == "↓ x ↑"

    def test_normalize_multi_measure_pattern(self):
        assert normalize_rhythm_input("d du udu / d d du") == "↓ ↓↑ ↑↓↑ / ↓ ↓ ↓↑"


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

    def test_folk_standard_preset_exists(self):
        p = get_preset_by_id("folk-standard")
        assert p is not None
        assert p["pattern"] == "↓ ↓↑ ↑↓↑"

    def test_pop_simple_preset_exists(self):
        p = get_preset_by_id("pop-simple")
        assert p is not None
        assert p["pattern"] == "↓ ↓ ↓↑"

    def test_rock_binaire_preset_exists(self):
        p = get_preset_by_id("rock-binaire")
        assert p is not None
        assert p["pattern"] == "↓ ↓ ↑↑"

    def test_ballade_preset_exists(self):
        p = get_preset_by_id("ballade")
        assert p is not None
        assert p["pattern"] == "↓ ↓↑ ↓ ↑"

    def test_waltz_basic_preset_exists(self):
        p = get_preset_by_id("waltz-basic")
        assert p is not None
        assert p["pattern"] == "↓ ↓ ↓"


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
    def test_pattern_and_subdivision(self):
        hint = _build_rhythm_hint(_sec({"pattern": "D-DU-UDU", "subdivision": "8th"}))
        assert hint == "D-DU-UDU [8th]"

    def test_pattern_only(self):
        hint = _build_rhythm_hint(_sec({"pattern": "↓ ↑"}))
        assert hint == "↓ ↑"

    def test_subdivision_only(self):
        hint = _build_rhythm_hint(_sec({"subdivision": "8th"}))
        assert hint == "[8th]"

    def test_no_rhythm(self):
        hint = _build_rhythm_hint(_sec())
        assert hint == ""

    def test_feel_field_ignored(self):
        """Ancien champ feel présent dans les JSON existants : ignoré silencieusement."""
        hint = _build_rhythm_hint(_sec({"pattern": "↓ ↑", "feel": "folk"}))
        assert hint == "↓ ↑"
        assert "folk" not in hint

    def test_empty_rhythm_object(self):
        hint = _build_rhythm_hint(_sec({}))
        assert hint == ""

    def test_rhythm_hint_fallback(self):
        """Sans clé rhythm, utilise rhythm_hint si présent (backward compat)."""
        sec = {"id": "x", "type": "verse", "rhythm_hint": "↓ ↑ · folk"}
        hint = _build_rhythm_hint(sec)
        assert hint == "↓ ↑ · folk"

    def test_rhythm_absent_no_hint(self):
        sec = {"id": "x", "type": "verse"}
        assert _build_rhythm_hint(sec) == ""

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


# ---------------------------------------------------------------------------
# Normalisation à la sauvegarde (apply_all_rhythm_edits)
# ---------------------------------------------------------------------------

class TestNormalizeOnSave:
    def _make_song(self):
        return {
            "meta": {"title": "T", "artist": "A", "slug": "t-a"},
            "sections": [{"id": "v1", "type": "verse", "label": "V"}],
            "structure_sequence": ["v1"],
        }

    def test_apply_all_rhythm_edits_normalizes_du(self):
        """apply_all_rhythm_edits convertit d/u minuscules en flèches Unicode."""
        from editor import apply_all_rhythm_edits
        result = apply_all_rhythm_edits(
            self._make_song(), {"v1": {"pattern": "d du udu", "feel": "folk"}}
        )
        assert result["sections"][0]["rhythm"]["pattern"] == "↓ ↓↑ ↑↓↑"

    def test_apply_all_rhythm_edits_preserves_arrows(self):
        """Les flèches déjà présentes restent inchangées."""
        from editor import apply_all_rhythm_edits
        result = apply_all_rhythm_edits(
            self._make_song(), {"v1": {"pattern": "↓ ↓↑ ↑↓↑", "feel": "folk"}}
        )
        assert result["sections"][0]["rhythm"]["pattern"] == "↓ ↓↑ ↑↓↑"

    def test_apply_all_rhythm_edits_preserves_slash(self):
        """Le séparateur / est conservé après normalisation."""
        from editor import apply_all_rhythm_edits
        result = apply_all_rhythm_edits(
            self._make_song(), {"v1": {"pattern": "d du / d d", "feel": ""}}
        )
        assert result["sections"][0]["rhythm"]["pattern"] == "↓ ↓↑ / ↓ ↓"

    def test_apply_all_rhythm_edits_mixed_input(self):
        """Mélange flèches + raccourcis : résultat entièrement normalisé."""
        from editor import apply_all_rhythm_edits
        result = apply_all_rhythm_edits(
            self._make_song(), {"v1": {"pattern": "↓ d↑", "feel": ""}}
        )
        assert result["sections"][0]["rhythm"]["pattern"] == "↓ ↓↑"
