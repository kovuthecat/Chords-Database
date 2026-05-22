"""
Génère un fichier .docx à partir d'un JSON song validé.
Usage : python scripts/generate_docx.py data/song_<slug>.json
"""

import io
import json
import sys
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH


def _ensure_utf8():
    if hasattr(sys.stdout, "buffer") and getattr(sys.stdout, "encoding", "").lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Polices et tailles
# ---------------------------------------------------------------------------

MONO_FONT   = "Consolas"       # lignes accords + paroles (monospace = alignement garanti)
BODY_FONT   = "Calibri"        # titres, en-têtes, méta

CHORD_SIZE  = Pt(13)           # accords : légèrement plus grand pour visibilité
LYRIC_SIZE  = Pt(12)           # paroles
SECTION_SIZE= Pt(13)           # [ SECTION ]
TITLE_SIZE  = Pt(22)           # titre chanson
ARTIST_SIZE = Pt(14)           # artiste
META_SIZE   = Pt(10)           # capo, tonalité, etc.

CHORD_COLOR = RGBColor(0x1F, 0x4E, 0x79)   # bleu marine bien lisible
SECTION_COLOR = RGBColor(0x20, 0x60, 0x20) # vert foncé pour les en-têtes de section


# ---------------------------------------------------------------------------
# Chargement et validation
# ---------------------------------------------------------------------------

def load_song(json_path: str) -> dict:
    path = Path(json_path)
    if not path.exists():
        print(f"Erreur : fichier introuvable : {json_path}")
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def check_validated(song: dict):
    status = song.get("validation", {}).get("status", "pending")
    if status != "user_validated":
        print(f"Erreur : le fichier n'est pas encore validé (status={status}).")
        print("Lance d'abord : python scripts/display_validation.py <fichier>")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Helpers paragraphe
# ---------------------------------------------------------------------------

def _p_keep_with_next(p):
    """Empêche un saut de page entre ce paragraphe et le suivant."""
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.page_break_before = False


def _p_no_space(p):
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.space_before = Pt(0)


def _p_small_space(p):
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.space_before = Pt(0)


# ---------------------------------------------------------------------------
# Blocs de contenu
# ---------------------------------------------------------------------------

def add_title_block(doc: Document, song: dict):
    meta = song["meta"]

    # Titre
    p = doc.add_paragraph()
    run = p.add_run(meta["title"].upper())
    run.bold = True
    run.font.name = BODY_FONT
    run.font.size = TITLE_SIZE
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)

    # Artiste
    p = doc.add_paragraph()
    run = p.add_run(meta["artist"])
    run.font.name = BODY_FONT
    run.font.size = ARTIST_SIZE
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(10)

    # Ligne méta : tonalité, capo, tempo
    meta_parts = []
    if meta.get("key"):
        mode = "majeur" if meta.get("key_mode") == "major" else "mineur"
        meta_parts.append(f"Tonalité : {meta['key']} {mode}")
    if meta.get("capo", 0):
        meta_parts.append(f"Capo : {meta['capo']}")
    if meta.get("tempo"):
        meta_parts.append(f"Tempo : ~{meta['tempo']} bpm")
    if meta.get("tuning") and meta["tuning"] != "standard":
        meta_parts.append(f"Accordage : {meta['tuning']}")

    if meta_parts:
        p = doc.add_paragraph("   |   ".join(meta_parts))
        run = p.runs[0]
        run.font.name = BODY_FONT
        run.font.size = META_SIZE
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(2)

    # Accords utilisés
    chords = [c for c in song.get("chords_used", []) if not c.startswith("_")]
    if chords:
        p = doc.add_paragraph("Accords : " + "  ".join(chords))
        run = p.runs[0]
        run.font.name = BODY_FONT
        run.font.size = META_SIZE
        run.bold = True
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(16)


def add_section_header(doc: Document, label: str):
    p = doc.add_paragraph()
    run = p.add_run(f"[ {label.upper()} ]")
    run.bold = True
    run.font.name = BODY_FONT
    run.font.size = SECTION_SIZE
    run.font.color.rgb = SECTION_COLOR
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(3)
    _p_keep_with_next(p)


def add_chord_grid(doc: Document, chord_grid: str, repeats: int = 1):
    """Ajoute une grille d'accords instrumentale. Gère les grilles multi-lignes (\n)."""
    lines = chord_grid.split("\n")
    for i, grid_line in enumerate(lines):
        grid_line = grid_line.strip()
        if not grid_line:
            continue
        # Indicateur ×N seulement sur la dernière ligne
        suffix = f"   ×{repeats}" if (repeats > 1 and i == len(lines) - 1) else ""
        p = doc.add_paragraph(grid_line + suffix)
        run = p.runs[0]
        run.font.name = MONO_FONT
        run.font.size = CHORD_SIZE
        run.bold = True
        run.font.color.rgb = CHORD_COLOR
        _p_keep_with_next(p)
        _p_no_space(p)
        p.paragraph_format.space_after = Pt(2)


def build_chord_line(chords: list, lyrics: str) -> str:
    """Place les accords à leurs positions en caractères au-dessus des paroles."""
    if not chords:
        return ""
    max_pos = max(c["position"] for c in chords)
    line_len = max(len(lyrics) + 4, max_pos + 8)
    result = [" "] * line_len
    for entry in sorted(chords, key=lambda x: x["position"]):
        pos = entry["position"]
        for i, ch in enumerate(entry["chord"]):
            if pos + i < len(result):
                result[pos + i] = ch
    return "".join(result).rstrip()


def add_chord_lyric_lines(doc: Document, lines: list):
    for line in lines:
        chords = line.get("chords", [])
        lyrics = line.get("lyrics", "")

        # Ligne d'accords
        if chords:
            chord_text = build_chord_line(chords, lyrics)
            p = doc.add_paragraph(chord_text)
            run = p.runs[0]
            run.font.name = MONO_FONT
            run.font.size = CHORD_SIZE
            run.bold = True
            run.font.color.rgb = CHORD_COLOR
            _p_no_space(p)
            _p_keep_with_next(p)   # colle au paragraphe suivant (paroles)

        # Ligne de paroles
        p = doc.add_paragraph(lyrics or "")
        run = p.runs[0]
        run.font.name = MONO_FONT
        run.font.size = LYRIC_SIZE
        _p_small_space(p)


# ---------------------------------------------------------------------------
# Rendu d'une section
# ---------------------------------------------------------------------------

def render_section(doc: Document, section: dict):
    label = section.get("label", section.get("type", "Section"))
    add_section_header(doc, label)

    repeats = section.get("repeats", 1)
    chord_grid = section.get("chord_grid")
    lines = section.get("lines", [])
    is_instr = section.get("is_instrumental", False)

    if is_instr:
        if chord_grid:
            add_chord_grid(doc, chord_grid, repeats)
        else:
            p = doc.add_paragraph("(instrumental)")
            run = p.runs[0]
            run.font.name = BODY_FONT
            run.font.size = META_SIZE
            run.italic = True
    else:
        if lines:
            add_chord_lyric_lines(doc, lines)
            if repeats > 1:
                p = doc.add_paragraph(f"(× {repeats})")
                run = p.runs[0]
                run.font.name = BODY_FONT
                run.font.size = META_SIZE
                run.italic = True
        elif chord_grid:
            add_chord_grid(doc, chord_grid, repeats)

    # Espace après la section
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.space_before = Pt(0)


# ---------------------------------------------------------------------------
# Génération du document
# ---------------------------------------------------------------------------

def set_margins(doc: Document, top=2.0, bottom=2.0, left=2.0, right=2.0):
    """Définit les marges en cm pour toutes les sections du document."""
    for section in doc.sections:
        section.top_margin    = Cm(top)
        section.bottom_margin = Cm(bottom)
        section.left_margin   = Cm(left)
        section.right_margin  = Cm(right)


def generate(song: dict, output_path: Path):
    doc = Document()
    set_margins(doc, top=2.0, bottom=2.0, left=2.5, right=2.0)

    add_title_block(doc, song)

    sections_by_id = {s["id"]: s for s in song.get("sections", [])}
    sequence = [
        x for x in song.get("structure_sequence", [])
        if isinstance(x, str) and not x.startswith("_comment")
    ]

    if sequence:
        # Toujours rendre la section complète, même en reprise
        for section_id in sequence:
            section = sections_by_id.get(section_id)
            if section:
                render_section(doc, section)
    else:
        for section in song.get("sections", []):
            render_section(doc, section)

    # Avertissements critiques en bas de document
    warnings = [w for w in song.get("warnings", []) if w.get("severity") in ("medium", "high")]
    if warnings:
        p = doc.add_paragraph("Notes :")
        p.runs[0].bold = True
        p.runs[0].font.name = BODY_FONT
        for w in warnings:
            p = doc.add_paragraph(f"• {w['message']}")
            p.runs[0].font.name = BODY_FONT
            p.runs[0].font.size = META_SIZE

    doc.save(output_path)
    print(f"DOCX généré : {output_path}")


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

def main():
    _ensure_utf8()
    if len(sys.argv) < 2:
        print("Usage : python scripts/generate_docx.py data/song_<slug>.json")
        sys.exit(1)

    json_path = sys.argv[1]
    song = load_song(json_path)
    check_validated(song)

    slug = song["meta"].get("slug", "output")
    output_path = Path("output") / f"song_{slug}.docx"
    output_path.parent.mkdir(exist_ok=True)

    generate(song, output_path)


if __name__ == "__main__":
    main()
