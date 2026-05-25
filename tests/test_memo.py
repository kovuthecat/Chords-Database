"""
Tests unitaires pour scripts/memo.py
Couvre : simplify_chord, build_chord_substitutions, is_simplification_relevant,
         _extract_progression, build_memo_lines
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from memo import (
    simplify_chord,
    build_chord_substitutions,
    is_simplification_relevant,
    _extract_progression,
    build_memo_lines,
    _extract_chord_tokens,
    _unique_ordered,
    _find_repeat_pattern,
    _consolidate_identical_lines,
    _extract_performance_lines,
)


# ---------------------------------------------------------------------------
# simplify_chord
# ---------------------------------------------------------------------------

class TestSimplifyChord:
    def test_accord_simple_inchange(self):
        result, changed = simplify_chord("C")
        assert result == "C"
        assert not changed

    def test_m7_simplifie(self):
        result, changed = simplify_chord("Am7")
        assert result == "Am"
        assert changed

    def test_maj7_simplifie(self):
        result, changed = simplify_chord("Cmaj7")
        assert result == "C"
        assert changed

    def test_sus4_simplifie(self):
        result, changed = simplify_chord("Dsus4")
        assert result == "D"
        assert changed

    def test_slash_chord_simplifie(self):
        result, changed = simplify_chord("C/G")
        assert result == "C"
        assert changed

    def test_add9_simplifie(self):
        result, changed = simplify_chord("Gadd9")
        assert result == "G"
        assert changed

    def test_dim_inchange(self):
        # Bdim → ne doit pas simplifier (le dim est structurel)
        result, changed = simplify_chord("Bdim")
        assert result == "Bdim"
        assert not changed

    def test_mineur_pur_inchange(self):
        result, changed = simplify_chord("Em")
        assert result == "Em"
        assert not changed

    def test_m7b5_simplifie(self):
        result, changed = simplify_chord("Bm7b5")
        assert result == "Bm"
        assert changed

    def test_7_sus4(self):
        result, changed = simplify_chord("A7sus4")
        assert result == "A"
        assert changed


# ---------------------------------------------------------------------------
# build_chord_substitutions
# ---------------------------------------------------------------------------

class TestBuildChordSubstitutions:
    def test_retourne_seul_les_changes(self):
        chords = ["C", "Am7", "F", "G"]
        subs = build_chord_substitutions(chords)
        assert "C" not in subs
        assert "F" not in subs
        assert "G" not in subs
        assert "Am7" in subs
        assert subs["Am7"] == "Am"

    def test_plusieurs_accords_simplifiables(self):
        chords = ["Cmaj7", "Am7", "Fmaj7", "G7sus4"]
        subs = build_chord_substitutions(chords)
        assert len(subs) == 4

    def test_liste_vide(self):
        assert build_chord_substitutions([]) == {}

    def test_tokens_internes_ignores(self):
        chords = ["_comment", "C", "Am7"]
        subs = build_chord_substitutions(chords)
        assert "_comment" not in subs


# ---------------------------------------------------------------------------
# is_simplification_relevant
# ---------------------------------------------------------------------------

class TestIsSimplificationRelevant:
    def test_vrai_si_deux_ou_plus(self):
        assert is_simplification_relevant({"Am7": "Am", "Cmaj7": "C"})

    def test_faux_si_moins_de_deux(self):
        assert not is_simplification_relevant({})
        assert not is_simplification_relevant({"Am7": "Am"})


# ---------------------------------------------------------------------------
# _extract_chord_tokens
# ---------------------------------------------------------------------------

class TestExtractChordTokens:
    def test_grille_simple(self):
        tokens = _extract_chord_tokens("| Am | F | C | G |")
        assert tokens == ["Am", "F", "C", "G"]

    def test_grille_avec_repetition(self):
        tokens = _extract_chord_tokens("| Em | D | x2")
        # Le marqueur x2 doit être supprimé
        assert "x2" not in tokens
        assert "Em" in tokens

    def test_grille_accords_enrichis(self):
        tokens = _extract_chord_tokens("| Am7 | F | Cmaj7 |")
        assert "Am7" in tokens
        assert "Cmaj7" in tokens


# ---------------------------------------------------------------------------
# _unique_ordered
# ---------------------------------------------------------------------------

class TestUniqueOrdered:
    def test_supprime_doublons(self):
        result = _unique_ordered(["C", "G", "C", "Am", "G"])
        assert result == "C G Am"

    def test_ordre_preserve(self):
        result = _unique_ordered(["Em", "D", "G", "C"])
        assert result == "Em D G C"


# ---------------------------------------------------------------------------
# _extract_progression
# ---------------------------------------------------------------------------

class TestExtractProgression:
    def test_depuis_summary_progression(self):
        section = {"summary_progression": "Am F C G", "chord_grid": None, "lines": []}
        assert _extract_progression(section) == "Am F C G"

    def test_depuis_chord_grid(self):
        section = {
            "summary_progression": None,
            "chord_grid": "| Em | D | G | C |",
            "lines": [],
        }
        prog = _extract_progression(section)
        assert "Em" in prog
        assert "D" in prog

    def test_depuis_lines(self):
        section = {
            "summary_progression": None,
            "chord_grid": None,
            "lines": [
                {"chords": [{"chord": "C", "position": 0}], "lyrics": "paroles"},
                {"chords": [{"chord": "G", "position": 0}], "lyrics": "suite"},
                {"chords": [{"chord": "Am", "position": 0}], "lyrics": "fin"},
            ],
        }
        prog = _extract_progression(section)
        assert "C" in prog
        assert "G" in prog
        assert "Am" in prog

    def test_section_vide(self):
        section = {"summary_progression": None, "chord_grid": None, "lines": []}
        assert _extract_progression(section) == ""


# ---------------------------------------------------------------------------
# build_memo_lines
# ---------------------------------------------------------------------------

class TestBuildMemoLines:
    def _make_song(self):
        return {
            "meta": {"title": "Test", "artist": "Artiste", "capo": 0},
            "sections": [
                {
                    "id": "intro_1",
                    "type": "intro",
                    "label": "Intro",
                    "is_instrumental": True,
                    "chord_grid": "| Am | F | C | G |",
                    "lines": [],
                    "repeats": 1,
                },
                {
                    "id": "verse_1",
                    "type": "verse",
                    "label": "Couplet",
                    "is_instrumental": False,
                    "chord_grid": None,
                    "lines": [
                        {"chords": [{"chord": "Am", "position": 0}], "lyrics": "paroles"},
                        {"chords": [{"chord": "F", "position": 0}], "lyrics": "suite"},
                    ],
                    "repeats": 1,
                },
                {
                    "id": "chorus_1",
                    "type": "chorus",
                    "label": "Refrain",
                    "is_instrumental": False,
                    "chord_grid": None,
                    "lines": [
                        {"chords": [{"chord": "C", "position": 0}], "lyrics": "refrain"},
                        {"chords": [{"chord": "G", "position": 0}], "lyrics": "suite"},
                    ],
                    "repeats": 2,
                },
            ],
            "structure_sequence": ["intro_1", "verse_1", "chorus_1"],
        }

    def test_nombre_lignes(self):
        song = self._make_song()
        lines = build_memo_lines(song)
        assert len(lines) == 3

    def test_labels(self):
        song = self._make_song()
        lines = build_memo_lines(song)
        labels = [l["label"] for l in lines]
        assert "Intro" in labels
        assert "Couplet" in labels
        assert "Refrain" in labels

    def test_progression_intro(self):
        song = self._make_song()
        lines = build_memo_lines(song)
        intro = next(l for l in lines if l["label"] == "Intro")
        assert "Am" in intro["progression"]

    def test_repeat_affiché(self):
        song = self._make_song()
        lines = build_memo_lines(song)
        refrain = next(l for l in lines if l["label"] == "Refrain")
        assert "2" in refrain["repeat"]


# ---------------------------------------------------------------------------
# _find_repeat_pattern
# ---------------------------------------------------------------------------

class TestFindRepeatPattern:
    def test_pattern_simple_x4(self):
        seqs = ["Am F G Am"] * 4
        pattern, repeat = _find_repeat_pattern(seqs)
        assert pattern == ["Am F G Am"]
        assert repeat == 4

    def test_pattern_deux_lignes_x3(self):
        seqs = ["Am C", "G F", "Am C", "G F", "Am C", "G F"]
        pattern, repeat = _find_repeat_pattern(seqs)
        assert pattern == ["Am C", "G F"]
        assert repeat == 3

    def test_pas_de_motif(self):
        seqs = ["C D Am", "G D", "C"]
        pattern, repeat = _find_repeat_pattern(seqs)
        assert repeat == 1
        assert pattern == seqs

    def test_element_unique(self):
        seqs = ["Am F"]
        pattern, repeat = _find_repeat_pattern(seqs)
        assert repeat == 1
        assert pattern == seqs

    def test_liste_vide(self):
        seqs = []
        pattern, repeat = _find_repeat_pattern(seqs)
        assert repeat == 1
        assert pattern == []


# ---------------------------------------------------------------------------
# _consolidate_identical_lines
# ---------------------------------------------------------------------------

class TestConsolidateIdenticalLines:
    def test_trois_identiques_fusionnes(self):
        lines = [
            {"chords": "Em C D G", "repeat": 1},
            {"chords": "Em C D G", "repeat": 1},
            {"chords": "Em C D G", "repeat": 1},
        ]
        result = _consolidate_identical_lines(lines)
        assert len(result) == 1
        assert result[0]["repeat"] == 3

    def test_non_consecutifs_non_fusionnes(self):
        lines = [
            {"chords": "Em C D G", "repeat": 1},
            {"chords": "Am F", "repeat": 1},
            {"chords": "Em C D G", "repeat": 1},
        ]
        result = _consolidate_identical_lines(lines)
        assert len(result) == 3

    def test_liste_vide(self):
        assert _consolidate_identical_lines([]) == []


# ---------------------------------------------------------------------------
# _extract_performance_lines
# ---------------------------------------------------------------------------

class TestExtractPerformanceLines:
    def test_depuis_summary_progression(self):
        section = {"summary_progression": "Em7 G A", "chord_grid": None, "lines": []}
        result = _extract_performance_lines(section)
        assert len(result) == 1
        assert result[0]["chords"] == "Em7 G A"
        assert result[0]["repeat"] == 1

    def test_depuis_chord_grid_une_ligne(self):
        section = {"chord_grid": "| Am | F | C | G |", "lines": []}
        result = _extract_performance_lines(section)
        assert len(result) == 1
        assert "Am" in result[0]["chords"]

    def test_depuis_chord_grid_multi_lignes(self):
        section = {
            "chord_grid": "| Am | C | G | Em |\n| Em | E  | E  |",
            "lines": [],
        }
        result = _extract_performance_lines(section)
        assert len(result) == 2

    def test_depuis_chord_grid_avec_marqueur_repetition(self):
        section = {
            "chord_grid": "| Em | D | Em |  x2",
            "lines": [],
        }
        result = _extract_performance_lines(section)
        assert result[0]["repeat"] == 2

    def test_depuis_lyrics_motif_detecte(self):
        # 4 lignes identiques → doit détecter (x4) et garder les doublons
        section = {
            "chord_grid": None,
            "lines": [
                {"chords": [{"chord": "Am"}, {"chord": "F"}, {"chord": "G"}, {"chord": "Am"}], "lyrics": "l1"},
                {"chords": [{"chord": "Am"}, {"chord": "F"}, {"chord": "G"}, {"chord": "Am"}], "lyrics": "l2"},
                {"chords": [{"chord": "Am"}, {"chord": "F"}, {"chord": "G"}, {"chord": "Am"}], "lyrics": "l3"},
                {"chords": [{"chord": "Am"}, {"chord": "F"}, {"chord": "G"}, {"chord": "Am"}], "lyrics": "l4"},
            ],
        }
        result = _extract_performance_lines(section)
        assert result[0]["repeat"] == 4
        # Am apparaît deux fois dans la progression (doublon conservé)
        assert result[0]["chords"].count("Am") == 2

    def test_depuis_lyrics_fallback_unique_ordered(self):
        # 3 lignes variées → pas de motif → fallback _unique_ordered
        section = {
            "chord_grid": None,
            "lines": [
                {"chords": [{"chord": "C"}], "lyrics": "l1"},
                {"chords": [{"chord": "D"}], "lyrics": "l2"},
                {"chords": [{"chord": "Am"}], "lyrics": "l3"},
            ],
        }
        result = _extract_performance_lines(section)
        assert result[0]["repeat"] == 1
        assert "C" in result[0]["chords"]
        assert "D" in result[0]["chords"]
        assert "Am" in result[0]["chords"]

    def test_section_vide(self):
        section = {"chord_grid": None, "lines": []}
        result = _extract_performance_lines(section)
        assert isinstance(result, list)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# build_memo_lines — champ "lines" (P4)
# ---------------------------------------------------------------------------

class TestBuildMemoLinesWithLines:
    def _make_song(self):
        return {
            "meta": {"title": "T", "artist": "A", "capo": 0},
            "sections": [
                {
                    "id": "chorus_1",
                    "type": "chorus",
                    "label": "Refrain",
                    "chord_grid": None,
                    "lines": [
                        {"chords": [{"chord": "Am"}, {"chord": "F"}, {"chord": "G"}, {"chord": "Am"}], "lyrics": "l1"},
                        {"chords": [{"chord": "Am"}, {"chord": "F"}, {"chord": "G"}, {"chord": "Am"}], "lyrics": "l2"},
                        {"chords": [{"chord": "Am"}, {"chord": "F"}, {"chord": "G"}, {"chord": "Am"}], "lyrics": "l3"},
                        {"chords": [{"chord": "Am"}, {"chord": "F"}, {"chord": "G"}, {"chord": "Am"}], "lyrics": "l4"},
                    ],
                    "repeats": 1,
                },
            ],
            "structure_sequence": ["chorus_1"],
        }

    def test_champ_lines_present(self):
        song = self._make_song()
        memo = build_memo_lines(song)
        assert len(memo) == 1
        assert "lines" in memo[0]

    def test_champ_progression_toujours_present(self):
        song = self._make_song()
        memo = build_memo_lines(song)
        assert "progression" in memo[0]

    def test_doublon_am_conserve_dans_lines(self):
        song = self._make_song()
        memo = build_memo_lines(song)
        refrain = memo[0]
        assert len(refrain["lines"]) >= 1
        assert refrain["lines"][0]["repeat"] == 4
        assert refrain["lines"][0]["chords"].count("Am") == 2
