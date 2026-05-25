"""
Tests unitaires pour scripts/editor.py
Couvre : replace_chord_in_song, apply_structure_edits, add_new_section,
         update_section_rhythm, apply_all_rhythm_edits, recalculate_chords_used.
"""
import sys
import copy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from editor import (
    replace_chord_in_song,
    apply_structure_edits,
    add_new_section,
    update_section_rhythm,
    apply_all_rhythm_edits,
    recalculate_chords_used,
    delete_chord_at,
    update_chord_at,
    insert_chord_at,
)


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

def _make_song() -> dict:
    return {
        "meta": {"title": "T", "artist": "A", "slug": "a-t"},
        "chords_used": ["Am", "C", "G", "F"],
        "structure_sequence": ["intro_1", "verse_1", "chorus_1"],
        "sections": [
            {
                "id": "intro_1",
                "type": "intro",
                "label": "Intro",
                "is_instrumental": True,
                "chord_grid": "| Am | C | G | F |",
                "summary_progression": "Am C G F",
                "performance_progression": [{"chords": "Am C", "repeat": 2}],
                "repeats": 1,
                "lines": [],
            },
            {
                "id": "verse_1",
                "type": "verse",
                "label": "Couplet",
                "is_instrumental": False,
                "repeats": 2,
                "lines": [
                    {
                        "lyrics": "Première ligne",
                        "chords": [
                            {"chord": "Am", "position": 0},
                            {"chord": "C",  "position": 10},
                        ],
                    }
                ],
            },
            {
                "id": "chorus_1",
                "type": "chorus",
                "label": "Refrain",
                "is_instrumental": False,
                "repeats": 1,
                "lines": [
                    {"lyrics": "Refrain line", "chords": [{"chord": "G", "position": 0}]}
                ],
            },
        ],
    }


# ---------------------------------------------------------------------------
# replace_chord_in_song — global
# ---------------------------------------------------------------------------

class TestReplaceChordGlobal:
    def test_replace_in_chord_grid(self):
        song = replace_chord_in_song(_make_song(), "Am", "A")
        assert "Am" not in song["sections"][0]["chord_grid"]
        assert "A" in song["sections"][0]["chord_grid"]

    def test_replace_in_summary_progression(self):
        song = replace_chord_in_song(_make_song(), "Am", "A")
        assert "Am" not in song["sections"][0]["summary_progression"]

    def test_replace_in_performance_progression(self):
        song = replace_chord_in_song(_make_song(), "Am", "A")
        assert song["sections"][0]["performance_progression"][0]["chords"] == "A C"

    def test_replace_in_lines_chords(self):
        song = replace_chord_in_song(_make_song(), "Am", "A")
        assert song["sections"][1]["lines"][0]["chords"][0]["chord"] == "A"

    def test_replace_updates_chords_used(self):
        song = replace_chord_in_song(_make_song(), "Am", "A")
        assert "Am" not in song["chords_used"]
        assert "A" in song["chords_used"]

    def test_replace_preserves_chords_used_order(self):
        song = replace_chord_in_song(_make_song(), "Am", "A")
        assert song["chords_used"][0] == "A"

    def test_no_partial_match(self):
        """Am ne doit pas remplacer Amaj7."""
        orig = _make_song()
        orig["sections"][0]["chord_grid"] = "| Amaj7 | Am |"
        song = replace_chord_in_song(orig, "Am", "A")
        assert "Amaj7" in song["sections"][0]["chord_grid"]
        assert "| A |" in song["sections"][0]["chord_grid"]

    def test_original_not_mutated(self):
        orig = _make_song()
        replace_chord_in_song(orig, "Am", "A")
        assert orig["chords_used"][0] == "Am"

    def test_same_old_new_noop(self):
        orig = _make_song()
        song = replace_chord_in_song(orig, "Am", "Am")
        assert song["chords_used"] == orig["chords_used"]


# ---------------------------------------------------------------------------
# replace_chord_in_song — sectionnel
# ---------------------------------------------------------------------------

class TestReplaceChordSection:
    def test_replaces_only_target_section(self):
        song = replace_chord_in_song(_make_song(), "Am", "A", section_id="intro_1")
        # intro_1 modifié
        assert "Am" not in song["sections"][0]["chord_grid"]
        # verse_1 non touché
        assert song["sections"][1]["lines"][0]["chords"][0]["chord"] == "Am"

    def test_recalculates_chords_used(self):
        """Après remplacement sectionnel, chords_used reflète la réalité."""
        song = replace_chord_in_song(_make_song(), "F", "Fmaj7", section_id="intro_1")
        assert "F" not in song["chords_used"]
        assert "Fmaj7" in song["chords_used"]

    def test_chord_still_in_other_section(self):
        """Am dans intro remplacé mais Am dans verse → doit rester dans chords_used."""
        song = replace_chord_in_song(_make_song(), "Am", "A", section_id="intro_1")
        assert "Am" in song["chords_used"]


# ---------------------------------------------------------------------------
# apply_structure_edits
# ---------------------------------------------------------------------------

class TestApplyStructureEdits:
    def test_reorder_sequence(self):
        song = apply_structure_edits(
            _make_song(),
            new_sequence=["chorus_1", "verse_1", "intro_1"],
            section_updates={},
        )
        assert song["structure_sequence"] == ["chorus_1", "verse_1", "intro_1"]

    def test_update_label(self):
        song = apply_structure_edits(
            _make_song(),
            new_sequence=["intro_1", "verse_1", "chorus_1"],
            section_updates={"verse_1": {"label": "Couplet 1"}},
        )
        verse = next(s for s in song["sections"] if s["id"] == "verse_1")
        assert verse["label"] == "Couplet 1"

    def test_update_type(self):
        song = apply_structure_edits(
            _make_song(),
            new_sequence=["intro_1", "verse_1", "chorus_1"],
            section_updates={"intro_1": {"type": "interlude"}},
        )
        intro = next(s for s in song["sections"] if s["id"] == "intro_1")
        assert intro["type"] == "interlude"

    def test_update_repeats(self):
        song = apply_structure_edits(
            _make_song(),
            new_sequence=["intro_1", "verse_1", "chorus_1"],
            section_updates={"verse_1": {"repeats": "3"}},
        )
        verse = next(s for s in song["sections"] if s["id"] == "verse_1")
        assert verse["repeats"] == 3

    def test_repeats_minimum_one(self):
        song = apply_structure_edits(
            _make_song(),
            new_sequence=["intro_1"],
            section_updates={"intro_1": {"repeats": "0"}},
        )
        intro = next(s for s in song["sections"] if s["id"] == "intro_1")
        assert intro["repeats"] == 1

    def test_comments_preserved(self):
        orig = _make_song()
        orig["structure_sequence"] = ["_comment: début", "intro_1", "verse_1"]
        song = apply_structure_edits(orig, ["verse_1", "intro_1"], {})
        assert song["structure_sequence"][0] == "_comment: début"
        assert song["structure_sequence"][1:] == ["verse_1", "intro_1"]

    def test_original_not_mutated(self):
        orig = _make_song()
        apply_structure_edits(orig, ["chorus_1"], {})
        assert orig["structure_sequence"] == ["intro_1", "verse_1", "chorus_1"]


# ---------------------------------------------------------------------------
# add_new_section
# ---------------------------------------------------------------------------

class TestAddNewSection:
    def test_section_added_to_list(self):
        song = add_new_section(_make_song(), "Pont", "bridge")
        ids = [s["id"] for s in song["sections"]]
        assert any(i.startswith("bridge_") for i in ids)

    def test_section_appended_to_sequence(self):
        song = add_new_section(_make_song(), "Pont", "bridge")
        new_id = song["sections"][-1]["id"]
        assert song["structure_sequence"][-1] == new_id

    def test_section_label_and_type(self):
        song = add_new_section(_make_song(), "Pont", "bridge")
        new_sec = song["sections"][-1]
        assert new_sec["label"] == "Pont"
        assert new_sec["type"] == "bridge"

    def test_chord_grid_optional(self):
        song = add_new_section(_make_song(), "Outro", "outro", chord_grid="| G | D |")
        new_sec = song["sections"][-1]
        assert new_sec["chord_grid"] == "| G | D |"
        assert new_sec["is_instrumental"] is True

    def test_no_chord_grid(self):
        song = add_new_section(_make_song(), "Outro", "outro")
        new_sec = song["sections"][-1]
        assert "chord_grid" not in new_sec
        assert new_sec["is_instrumental"] is False

    def test_id_collision_avoided(self):
        orig = _make_song()
        song1 = add_new_section(orig, "Couplet 2", "verse")
        song2 = add_new_section(song1, "Couplet 3", "verse")
        ids = [s["id"] for s in song2["sections"]]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# update_section_rhythm / apply_all_rhythm_edits
# ---------------------------------------------------------------------------

class TestRhythmEdits:
    def test_set_pattern_and_feel(self):
        song = update_section_rhythm(_make_song(), "intro_1", "D DU UDU", "straight")
        intro = next(s for s in song["sections"] if s["id"] == "intro_1")
        assert intro["rhythm"]["pattern"] == "D DU UDU"
        assert intro["rhythm"]["feel"] == "straight"

    def test_empty_removes_rhythm_key(self):
        orig = _make_song()
        orig["sections"][0]["rhythm"] = {"pattern": "D", "feel": "straight"}
        song = update_section_rhythm(orig, "intro_1", "", "")
        intro = next(s for s in song["sections"] if s["id"] == "intro_1")
        assert "rhythm" not in intro

    def test_apply_all_rhythm_edits(self):
        edits = {
            "intro_1": {"pattern": "D DU", "feel": "swing"},
            "verse_1": {"pattern": "DU DU", "feel": "straight"},
        }
        song = apply_all_rhythm_edits(_make_song(), edits)
        intro = next(s for s in song["sections"] if s["id"] == "intro_1")
        verse = next(s for s in song["sections"] if s["id"] == "verse_1")
        assert intro["rhythm"]["pattern"] == "D DU"
        assert verse["rhythm"]["feel"] == "straight"

    def test_original_not_mutated(self):
        orig = _make_song()
        update_section_rhythm(orig, "intro_1", "D", "swing")
        assert "rhythm" not in orig["sections"][0]


# ---------------------------------------------------------------------------
# recalculate_chords_used
# ---------------------------------------------------------------------------

class TestRecalculateChordsUsed:
    def test_collects_from_chord_grid(self):
        chords = recalculate_chords_used(_make_song())
        assert "Am" in chords
        assert "C" in chords

    def test_no_duplicates(self):
        chords = recalculate_chords_used(_make_song())
        assert len(chords) == len(set(chords))

    def test_order_of_appearance(self):
        song = _make_song()
        chords = recalculate_chords_used(song)
        # Am apparaît avant G dans intro_1
        assert chords.index("Am") < chords.index("G")


# ---------------------------------------------------------------------------
# delete_chord_at
# ---------------------------------------------------------------------------

class TestDeleteChordAt:
    def test_removes_correct_chord(self):
        song = delete_chord_at(_make_song(), "verse_1", 0, 0)
        chords = song["sections"][1]["lines"][0]["chords"]
        assert len(chords) == 1
        assert chords[0]["chord"] == "C"

    def test_wrong_section_id_noop(self):
        orig = _make_song()
        song = delete_chord_at(orig, "INEXISTANT", 0, 0)
        assert len(song["sections"][1]["lines"][0]["chords"]) == 2

    def test_out_of_range_index_noop(self):
        orig = _make_song()
        song = delete_chord_at(orig, "verse_1", 0, 99)
        assert len(song["sections"][1]["lines"][0]["chords"]) == 2

    def test_recalculates_chords_used(self):
        song = delete_chord_at(_make_song(), "verse_1", 0, 0)
        # Am encore dans intro_1 → doit rester
        assert "Am" in song["chords_used"]

    def test_original_not_mutated(self):
        orig = _make_song()
        delete_chord_at(orig, "verse_1", 0, 0)
        assert len(orig["sections"][1]["lines"][0]["chords"]) == 2


# ---------------------------------------------------------------------------
# update_chord_at
# ---------------------------------------------------------------------------

class TestUpdateChordAt:
    def test_updates_specific_chord(self):
        song = update_chord_at(_make_song(), "verse_1", 0, 0, "Dm")
        chords = song["sections"][1]["lines"][0]["chords"]
        assert chords[0]["chord"] == "Dm"
        assert chords[1]["chord"] == "C"  # inchangé

    def test_position_preserved(self):
        song = update_chord_at(_make_song(), "verse_1", 0, 0, "Dm")
        chords = song["sections"][1]["lines"][0]["chords"]
        assert chords[0]["position"] == 0

    def test_does_not_touch_other_occurrences(self):
        """Am dans verse modifié → Am dans intro reste intact."""
        song = update_chord_at(_make_song(), "verse_1", 0, 0, "Dm")
        intro = next(s for s in song["sections"] if s["id"] == "intro_1")
        assert "Am" in intro["chord_grid"]

    def test_empty_new_chord_noop(self):
        orig = _make_song()
        song = update_chord_at(orig, "verse_1", 0, 0, "")
        assert song["sections"][1]["lines"][0]["chords"][0]["chord"] == "Am"

    def test_updates_chords_used(self):
        song = update_chord_at(_make_song(), "chorus_1", 0, 0, "Em")
        assert "Em" in song["chords_used"]


# ---------------------------------------------------------------------------
# insert_chord_at
# ---------------------------------------------------------------------------

class TestInsertChordAt:
    def test_inserts_chord(self):
        song = insert_chord_at(_make_song(), "verse_1", 0, "F", 5)
        chords = song["sections"][1]["lines"][0]["chords"]
        chord_vals = [c["chord"] for c in chords]
        assert "F" in chord_vals

    def test_sorted_by_position(self):
        song = insert_chord_at(_make_song(), "verse_1", 0, "F", 5)
        chords = song["sections"][1]["lines"][0]["chords"]
        positions = [c["position"] for c in chords]
        assert positions == sorted(positions)

    def test_adds_to_chords_used(self):
        song = insert_chord_at(_make_song(), "verse_1", 0, "Bm", 8)
        assert "Bm" in song["chords_used"]

    def test_empty_chord_noop(self):
        orig = _make_song()
        song = insert_chord_at(orig, "verse_1", 0, "", 0)
        assert len(song["sections"][1]["lines"][0]["chords"]) == 2

    def test_original_not_mutated(self):
        orig = _make_song()
        insert_chord_at(orig, "verse_1", 0, "F", 5)
        assert len(orig["sections"][1]["lines"][0]["chords"]) == 2
