"""
Interface web Chords.
Lance : python app.py  puis ouvrir http://localhost:5000

Workflow :
  Upload JSON → validation → génération DOCX + aperçu HTML → corrections → export 2 PDFs split
  Bibliothèque : /library → consultation, édition, régénération par morceau

Backend de stockage : STORAGE_BACKEND=local (défaut) ou STORAGE_BACKEND=supabase
"""
import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, send_from_directory, url_for

ROOT_DIR    = Path(__file__).parent
SCRIPTS_DIR = ROOT_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from config import STORAGE_BACKEND                                          # noqa: E402
from storage import get_storage                                             # noqa: E402
from validate_song_json import validate_song_json                           # noqa: E402
from generate_docx import generate, generate_pdf, generate_split_pdf       # noqa: E402
from editor import (                                                        # noqa: E402
    replace_chord_in_song,
    apply_structure_edits,
    add_new_section,
    apply_all_rhythm_edits,
    delete_chord_at,
    update_chord_at,
    insert_chord_at,
    move_chord_at,
    set_chord_position,
    update_instr_chord,
    delete_instr_chord,
    insert_instr_chord,
    update_lyrics_at,
)
from transpose import transpose_song as _do_transpose                       # noqa: E402
from memo import build_memo_lines                                           # noqa: E402

app = Flask(__name__)

SECTION_TYPES = ["intro", "verse", "chorus", "pre-chorus", "bridge", "interlude", "solo", "outro"]


@app.template_filter("parse_chord_grid")
def parse_chord_grid_filter(chord_grid: str) -> list:
    result = []
    for li, line in enumerate(chord_grid.split("\n")):
        stripped = line.strip()
        if not stripped:
            continue
        tokens = [p.strip() for p in stripped.split("|") if p.strip()]
        chords = [{"ci": ci, "chord": chord} for ci, chord in enumerate(tokens)]
        result.append({"li": li, "chords": chords})
    return result


@app.template_filter("word_positions")
def word_positions_filter(lyrics: str) -> list:
    if not lyrics:
        return []
    result = []
    pos = 0
    for token in lyrics.split(" "):
        if token:
            result.append({"word": token, "pos": pos})
        pos += len(token) + 1
    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_song(slug: str) -> dict | None:
    return get_storage().get_song(slug)


def _save_song(slug: str, song: dict) -> None:
    get_storage().save_song(song)


def _list_songs() -> list[dict]:
    return get_storage().list_songs()


def _split_pdf_filename(song: dict, part: str) -> str:
    from generate_docx import _split_pdf_filename as _fn
    return _fn(song, part)


def _generate_outputs(song: dict) -> dict:
    """Génère DOCX et PDF preview.
    - Local  : écrit dans output/
    - Cloud  : écrit dans /tmp (éphémère, non persisté)
    """
    slug = song["meta"]["slug"]

    if STORAGE_BACKEND == "supabase":
        tmp_dir = Path(tempfile.gettempdir()) / "chords" / slug
        tmp_dir.mkdir(parents=True, exist_ok=True)
        docx_path = tmp_dir / f"song_{slug}.docx"
        generate(song, docx_path)
        pdf_path  = None
        pdf_error = None
        try:
            pdf_path = tmp_dir / f"song_{slug}.pdf"
            generate_pdf(song, pdf_path)
        except Exception as e:
            pdf_error = str(e)
            pdf_path  = None
        return {"docx": docx_path, "pdf": pdf_path, "pdf_error": pdf_error}

    # Mode local — comportement original
    from config import OUTPUT_DIR
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    docx_path = OUTPUT_DIR / f"song_{slug}.docx"
    generate(song, docx_path)
    pdf_path  = None
    pdf_error = None
    try:
        pdf_path = OUTPUT_DIR / f"song_{slug}.pdf"
        generate_pdf(song, pdf_path)
    except Exception as e:
        pdf_error = str(e)
        pdf_path  = None
    return {"docx": docx_path, "pdf": pdf_path, "pdf_error": pdf_error}


def _generate_and_upload_splits(song: dict, slug: str) -> None:
    """Génère les 2 PDFs split puis les persiste (local : PDF_EXPORT_DIR, cloud : Supabase Storage)."""
    storage = get_storage()

    if STORAGE_BACKEND == "supabase":
        tmp_dir = Path(tempfile.gettempdir()) / "chords_export" / slug
        tmp_dir.mkdir(parents=True, exist_ok=True)
        for part in ("chords", "memo"):
            filename = _split_pdf_filename(song, part)
            tmp_path = tmp_dir / filename
            generate_pdf(song, tmp_path, parts=[part])
            storage.save_pdf_export(slug, filename, tmp_path.read_bytes())
            tmp_path.unlink(missing_ok=True)
        return

    # Mode local : utilise le chemin generate_split_pdf standard
    generate_split_pdf(song, slug)


def _song_template_data(song: dict, slug: str, **extra) -> dict:
    """Construit le dict complet de variables pour le template song.html."""
    storage = get_storage()
    sections_by_id = {s["id"]: s for s in song.get("sections", [])}

    structure_items = [
        sid for sid in song.get("structure_sequence", [])
        if isinstance(sid, str) and not sid.startswith("_comment")
    ]

    seen_ids: set = set()
    unique_sections = []
    for sid in structure_items:
        if sid not in seen_ids and sid in sections_by_id:
            seen_ids.add(sid)
            unique_sections.append(sections_by_id[sid])

    sections_data = {
        s["id"]: {
            "label":   s.get("label", s.get("type", s["id"])),
            "type":    s.get("type", "verse"),
            "repeats": s.get("repeats", 1),
        }
        for s in song.get("sections", [])
    }

    chords_name = _split_pdf_filename(song, "chords")
    memo_name   = _split_pdf_filename(song, "memo")

    if STORAGE_BACKEND == "supabase":
        from config import OUTPUT_DIR
        docx_exists = False
        pdf_exists  = False
    else:
        from config import OUTPUT_DIR
        docx_exists = (OUTPUT_DIR / f"song_{slug}.docx").exists()
        pdf_exists  = (OUTPUT_DIR / f"song_{slug}.pdf").exists()

    pdf_chords_url = storage.get_pdf_export_url(slug, chords_name)
    pdf_memo_url   = storage.get_pdf_export_url(slug, memo_name)

    return dict(
        song=song,
        slug=slug,
        docx_exists=docx_exists,
        pdf_exists=pdf_exists,
        export_dir=storage.export_dir_display,
        pdf_chords_exists=(pdf_chords_url is not None),
        pdf_memo_exists=(pdf_memo_url is not None),
        pdf_chords_name=chords_name,
        pdf_memo_name=memo_name,
        pdf_chords_url=pdf_chords_url or f"/export/{chords_name}",
        pdf_memo_url=pdf_memo_url   or f"/export/{memo_name}",
        structure_items=structure_items,
        sections_by_id=sections_by_id,
        sections_data_json=json.dumps(sections_data, ensure_ascii=False),
        unique_sections=unique_sections,
        section_types=SECTION_TYPES,
        edit_ok=request.args.get("edit_ok"),
        edit_error=request.args.get("edit_error"),
        gen_warning=request.args.get("gen_warning"),
        exported=request.args.get("exported"),
        **extra,
    )


def _save_and_redirect(slug: str, song: dict, ok_msg: str):
    errors = validate_song_json(song)
    if errors:
        return redirect(url_for("song_page", slug=slug, edit_error=errors[0]))
    _save_song(slug, song)
    return redirect(url_for("song_page", slug=slug, edit_ok=ok_msg))


# ---------------------------------------------------------------------------
# Routes — navigation principale
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return redirect(url_for("library"))


@app.route("/add")
def add_song():
    return render_template("index.html", songs=_list_songs())


@app.route("/upload", methods=["POST"])
def upload():
    f = request.files.get("json_file")
    if not f or f.filename == "":
        return render_template("index.html", songs=_list_songs(),
                               error="Aucun fichier sélectionné.")
    try:
        song = json.loads(f.read().decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        return render_template("index.html", songs=_list_songs(),
                               error=f"JSON invalide : {e}")

    errors = validate_song_json(song)
    if errors:
        return render_template("index.html", songs=_list_songs(), errors=errors)

    slug = song["meta"]["slug"]
    _save_song(slug, song)

    result = _generate_outputs(song)
    kw = {"gen_warning": result["pdf_error"]} if result.get("pdf_error") else {}
    return redirect(url_for("song_page", slug=slug, **kw))


@app.route("/song/<slug>")
def song_page(slug: str):
    song = _load_song(slug)
    if song is None:
        return "Chanson introuvable.", 404
    return render_template("song.html",
                           **_song_template_data(song, slug),
                           backups=get_storage().list_backups(slug))


@app.route("/song/<slug>/regenerate", methods=["POST"])
def regenerate(slug: str):
    f = request.files.get("json_file")
    if f and f.filename != "":
        try:
            song = json.loads(f.read().decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            orig = _load_song(slug)
            return render_template("song.html",
                                   **_song_template_data(orig or {}, slug,
                                                         error=f"JSON invalide : {e}"))
        errors = validate_song_json(song)
        if errors:
            return render_template("song.html",
                                   **_song_template_data(song, slug, errors=errors))
        _save_song(slug, song)
    else:
        song = _load_song(slug)
        if song is None:
            return "Chanson introuvable.", 404

    result = _generate_outputs(song)
    kw = {"gen_warning": result["pdf_error"]} if result.get("pdf_error") else {}
    return redirect(url_for("song_page", slug=slug, **kw))


@app.route("/song/<slug>/export-split", methods=["POST"])
def export_split(slug: str):
    song = _load_song(slug)
    if song is None:
        return "Chanson introuvable.", 404

    song.setdefault("validation", {})
    song["validation"]["status"] = "user_validated"
    song["validation"]["validated_at"] = datetime.now().isoformat()
    _save_song(slug, song)

    try:
        _generate_and_upload_splits(song, slug)
    except Exception as e:
        return render_template("song.html",
                               **_song_template_data(song, slug,
                                                     error=f"Erreur export PDF : {e}"))

    return redirect(url_for("song_page", slug=slug, exported=1))


@app.route("/output/<path:filename>")
def serve_output(filename: str):
    if STORAGE_BACKEND == "supabase":
        slug = filename.removeprefix("song_").rsplit(".", 1)[0]
        tmp_dir = Path(tempfile.gettempdir()) / "chords" / slug
        tmp_path = tmp_dir / filename
        if tmp_path.exists():
            return send_from_directory(str(tmp_dir), filename)
        return "Fichier non généré — utilisez le bouton Régénérer.", 404
    from config import OUTPUT_DIR
    return send_from_directory(OUTPUT_DIR, filename)


@app.route("/export/<path:filename>")
def serve_export(filename: str):
    """Sert un PDF exporté (local) ou redirige vers Supabase Storage (cloud)."""
    if STORAGE_BACKEND == "supabase":
        # En mode cloud le lien direct passe par /export/<filename>
        # On ne connaît pas le slug ici — on retourne 404 proprement
        # Les vraies URLs sont les pdf_chords_url / pdf_memo_url du template
        return "Accès direct non disponible en mode cloud — utilisez les liens de la fiche.", 404
    from config import PDF_EXPORT_DIR
    return send_from_directory(PDF_EXPORT_DIR, filename)


@app.route("/library")
def library():
    songs = _list_songs()
    for s in songs:
        if s.get("mtime"):
            s["mdate"] = datetime.fromtimestamp(s["mtime"]).strftime("%d/%m/%Y")
        else:
            s["mdate"] = "—"
    keys = sorted({s["key"] for s in songs if s.get("key")})
    return render_template("library.html", songs=songs,
                           export_dir=get_storage().export_dir_display, keys=keys)


@app.route("/song/<slug>/save-all", methods=["POST"])
def save_all(slug: str):
    song = _load_song(slug)
    if song is None:
        return jsonify(error="Chanson introuvable"), 404

    raw_seq = request.form.get("new_sequence", "[]")
    try:
        new_sequence = json.loads(raw_seq)
    except (ValueError, json.JSONDecodeError):
        new_sequence = [x.strip() for x in raw_seq.split(",") if x.strip()]

    section_updates: dict = {}
    for s in song.get("sections", []):
        sid = s["id"]
        upd = {}
        if f"label_{sid}" in request.form:
            upd["label"] = request.form[f"label_{sid}"]
        if f"type_{sid}" in request.form:
            upd["type"] = request.form[f"type_{sid}"]
        if f"repeats_{sid}" in request.form:
            upd["repeats"] = request.form[f"repeats_{sid}"]
        if upd:
            section_updates[sid] = upd

    song = apply_structure_edits(song, new_sequence, section_updates)

    rhythm_edits: dict = {}
    for s in song.get("sections", []):
        sid     = s["id"]
        pattern = request.form.get(f"pattern_{sid}", "").strip()
        feel    = request.form.get(f"feel_{sid}", "").strip()
        if pattern or feel or s.get("rhythm"):
            rhythm_edits[sid] = {"pattern": pattern, "feel": feel}

    song = apply_all_rhythm_edits(song, rhythm_edits)

    errors = validate_song_json(song)
    if errors:
        return jsonify(error=errors[0]), 400

    _save_song(slug, song)
    return jsonify(ok=True)


@app.route("/song/<slug>/delete", methods=["POST"])
def delete_song(slug: str):
    get_storage().delete_song(slug)
    return redirect(url_for("library"))


# ---------------------------------------------------------------------------
# Routes — éditeur de corrections
# ---------------------------------------------------------------------------

@app.route("/song/<slug>/replace-chord", methods=["POST"])
def replace_chord(slug: str):
    song = _load_song(slug)
    if song is None:
        return "Chanson introuvable.", 404

    old_chord  = request.form.get("old_chord", "").strip()
    new_chord  = request.form.get("new_chord", "").strip()
    section_id = request.form.get("section_id") or None

    if not old_chord or not new_chord:
        return redirect(url_for("song_page", slug=slug,
                                edit_error="Les deux champs accord sont obligatoires."))

    song = replace_chord_in_song(song, old_chord, new_chord, section_id)
    scope = f"section {section_id}" if section_id else "tout le morceau"
    return _save_and_redirect(slug, song, f"{old_chord} → {new_chord} ({scope})")


@app.route("/song/<slug>/edit-structure", methods=["POST"])
def edit_structure(slug: str):
    song = _load_song(slug)
    if song is None:
        return "Chanson introuvable.", 404

    raw_seq = request.form.get("new_sequence", "[]")
    try:
        new_sequence = json.loads(raw_seq)
    except (ValueError, json.JSONDecodeError):
        new_sequence = [x.strip() for x in raw_seq.split(",") if x.strip()]

    section_updates: dict = {}
    for s in song.get("sections", []):
        sid = s["id"]
        upd = {}
        if f"label_{sid}" in request.form:
            upd["label"] = request.form[f"label_{sid}"]
        if f"type_{sid}" in request.form:
            upd["type"] = request.form[f"type_{sid}"]
        if f"repeats_{sid}" in request.form:
            upd["repeats"] = request.form[f"repeats_{sid}"]
        if upd:
            section_updates[sid] = upd

    song = apply_structure_edits(song, new_sequence, section_updates)
    return _save_and_redirect(slug, song, "Structure sauvegardée.")


@app.route("/song/<slug>/add-section", methods=["POST"])
def add_section(slug: str):
    song = _load_song(slug)
    if song is None:
        return "Chanson introuvable.", 404

    label        = request.form.get("label", "").strip()
    section_type = request.form.get("type", "verse").strip()
    chord_grid   = request.form.get("chord_grid", "").strip() or None

    if not label:
        return redirect(url_for("song_page", slug=slug,
                                edit_error="Le label de la section est obligatoire."))

    song = add_new_section(song, label, section_type, chord_grid)
    return _save_and_redirect(slug, song, f"Section « {label} » ajoutée.")


@app.route("/song/<slug>/edit-rhythm", methods=["POST"])
def edit_rhythm(slug: str):
    song = _load_song(slug)
    if song is None:
        return "Chanson introuvable.", 404

    edits: dict = {}
    for s in song.get("sections", []):
        sid     = s["id"]
        pattern = request.form.get(f"pattern_{sid}", "").strip()
        feel    = request.form.get(f"feel_{sid}", "").strip()
        if pattern or feel or s.get("rhythm"):
            edits[sid] = {"pattern": pattern, "feel": feel}

    song = apply_all_rhythm_edits(song, edits)
    return _save_and_redirect(slug, song, "Rythmes sauvegardés.")


# ---------------------------------------------------------------------------
# Routes — aperçu interactif (AJAX)
# ---------------------------------------------------------------------------

@app.route("/song/<slug>/preview-html")
def song_preview_html(slug: str):
    song = _load_song(slug)
    if song is None:
        return "Chanson introuvable.", 404
    sections_by_id = {s["id"]: s for s in song.get("sections", [])}
    structure_items = [
        sid for sid in song.get("structure_sequence", [])
        if isinstance(sid, str) and not sid.startswith("_comment")
    ]
    return render_template("_preview.html", song=song, slug=slug,
                           sections_by_id=sections_by_id,
                           structure_items=structure_items)


@app.route("/song/<slug>/chord-at/update", methods=["POST"])
def chord_at_update(slug: str):
    song = _load_song(slug)
    if song is None:
        return jsonify(error="Chanson introuvable"), 404
    try:
        section_id  = request.form["section_id"]
        line_index  = int(request.form["line_index"])
        chord_index = int(request.form["chord_index"])
        new_chord   = request.form.get("new_chord", "").strip()
    except (KeyError, ValueError):
        return jsonify(error="Paramètres invalides"), 400
    if not new_chord:
        return jsonify(error="Accord manquant"), 400
    song = update_chord_at(song, section_id, line_index, chord_index, new_chord)
    errors = validate_song_json(song)
    if errors:
        return jsonify(error=errors[0]), 400
    _save_song(slug, song)
    return jsonify(ok=True)


@app.route("/song/<slug>/chord-at/delete", methods=["POST"])
def chord_at_delete(slug: str):
    song = _load_song(slug)
    if song is None:
        return jsonify(error="Chanson introuvable"), 404
    try:
        section_id  = request.form["section_id"]
        line_index  = int(request.form["line_index"])
        chord_index = int(request.form["chord_index"])
    except (KeyError, ValueError):
        return jsonify(error="Paramètres invalides"), 400
    song = delete_chord_at(song, section_id, line_index, chord_index)
    errors = validate_song_json(song)
    if errors:
        return jsonify(error=errors[0]), 400
    _save_song(slug, song)
    return jsonify(ok=True)


@app.route("/song/<slug>/chord-at/insert", methods=["POST"])
def chord_at_insert(slug: str):
    song = _load_song(slug)
    if song is None:
        return jsonify(error="Chanson introuvable"), 404
    try:
        section_id = request.form["section_id"]
        line_index = int(request.form["line_index"])
        position   = int(request.form["position"])
        chord      = request.form.get("chord", "").strip()
    except (KeyError, ValueError):
        return jsonify(error="Paramètres invalides"), 400
    if not chord:
        return jsonify(error="Accord manquant"), 400
    song = insert_chord_at(song, section_id, line_index, chord, position)
    errors = validate_song_json(song)
    if errors:
        return jsonify(error=errors[0]), 400
    _save_song(slug, song)
    return jsonify(ok=True)


@app.route("/song/<slug>/chord-at/move", methods=["POST"])
def chord_at_move(slug: str):
    song = _load_song(slug)
    if song is None:
        return jsonify(error="Chanson introuvable"), 404
    try:
        section_id  = request.form["section_id"]
        line_index  = int(request.form["line_index"])
        chord_index = int(request.form["chord_index"])
        delta       = int(request.form["delta"])
    except (KeyError, ValueError):
        return jsonify(error="Paramètres invalides"), 400
    song = move_chord_at(song, section_id, line_index, chord_index, delta)
    errors = validate_song_json(song)
    if errors:
        return jsonify(error=errors[0]), 400
    _save_song(slug, song)
    return jsonify(ok=True)


@app.route("/song/<slug>/chord-at/set-position", methods=["POST"])
def chord_at_set_position(slug: str):
    song = _load_song(slug)
    if song is None:
        return jsonify(error="Chanson introuvable"), 404
    try:
        section_id  = request.form["section_id"]
        line_index  = int(request.form["line_index"])
        chord_index = int(request.form["chord_index"])
        position    = int(request.form["position"])
    except (KeyError, ValueError):
        return jsonify(error="Paramètres invalides"), 400
    if position < 0:
        return jsonify(error="Position invalide"), 400
    song = set_chord_position(song, section_id, line_index, chord_index, position)
    errors = validate_song_json(song)
    if errors:
        return jsonify(error=errors[0]), 400
    _save_song(slug, song)
    return jsonify(ok=True)


@app.route("/song/<slug>/instr-chord/update", methods=["POST"])
def instr_chord_update(slug: str):
    song = _load_song(slug)
    if song is None:
        return jsonify(error="Chanson introuvable"), 404
    try:
        section_id  = request.form["section_id"]
        instr_type  = request.form["instr_type"]
        chord_index = int(request.form["chord_index"])
        new_chord   = request.form.get("new_chord", "").strip()
        ppi = int(request.form.get("ppi", 0))
        li  = int(request.form.get("li", 0))
    except (KeyError, ValueError):
        return jsonify(error="Paramètres invalides"), 400
    if not new_chord:
        return jsonify(error="Accord manquant"), 400
    song = update_instr_chord(song, section_id, instr_type, chord_index, new_chord, ppi=ppi, li=li)
    errors = validate_song_json(song)
    if errors:
        return jsonify(error=errors[0]), 400
    _save_song(slug, song)
    return jsonify(ok=True)


@app.route("/song/<slug>/instr-chord/delete", methods=["POST"])
def instr_chord_delete(slug: str):
    song = _load_song(slug)
    if song is None:
        return jsonify(error="Chanson introuvable"), 404
    try:
        section_id  = request.form["section_id"]
        instr_type  = request.form["instr_type"]
        chord_index = int(request.form["chord_index"])
        ppi = int(request.form.get("ppi", 0))
        li  = int(request.form.get("li", 0))
    except (KeyError, ValueError):
        return jsonify(error="Paramètres invalides"), 400
    song = delete_instr_chord(song, section_id, instr_type, chord_index, ppi=ppi, li=li)
    errors = validate_song_json(song)
    if errors:
        return jsonify(error=errors[0]), 400
    _save_song(slug, song)
    return jsonify(ok=True)


@app.route("/song/<slug>/instr-chord/insert", methods=["POST"])
def instr_chord_insert(slug: str):
    song = _load_song(slug)
    if song is None:
        return jsonify(error="Chanson introuvable"), 404
    try:
        section_id = request.form["section_id"]
        instr_type = request.form["instr_type"]
        insert_at  = int(request.form["insert_at"])
        chord      = request.form.get("chord", "").strip()
        ppi = int(request.form.get("ppi", 0))
        li  = int(request.form.get("li", 0))
    except (KeyError, ValueError):
        return jsonify(error="Paramètres invalides"), 400
    if not chord:
        return jsonify(error="Accord manquant"), 400
    song = insert_instr_chord(song, section_id, instr_type, insert_at, chord, ppi=ppi, li=li)
    errors = validate_song_json(song)
    if errors:
        return jsonify(error=errors[0]), 400
    _save_song(slug, song)
    return jsonify(ok=True)


@app.route("/song/<slug>/lyrics-at/update", methods=["POST"])
def lyrics_at_update(slug: str):
    song = _load_song(slug)
    if song is None:
        return jsonify(error="Chanson introuvable"), 404
    try:
        section_id = request.form["section_id"]
        line_index = int(request.form["line_index"])
        new_lyrics = request.form.get("new_lyrics", "")
    except (KeyError, ValueError):
        return jsonify(error="Paramètres invalides"), 400
    song = update_lyrics_at(song, section_id, line_index, new_lyrics)
    _save_song(slug, song)
    return jsonify(ok=True)


@app.route("/song/<slug>/restore/<backup_filename>", methods=["POST"])
def restore_backup_route(slug: str, backup_filename: str):
    storage = get_storage()
    restored = storage.restore_backup(slug, backup_filename)
    if restored is None:
        return redirect(url_for("song_page", slug=slug,
                                edit_error="Backup introuvable ou invalide."))
    errors = validate_song_json(restored)
    if errors:
        return redirect(url_for("song_page", slug=slug,
                                edit_error=f"Backup invalide : {errors[0]}"))
    _save_song(slug, restored)
    try:
        _generate_outputs(restored)
    except Exception:
        pass
    return redirect(url_for("song_page", slug=slug, edit_ok="Version restaurée depuis backup."))


@app.route("/song/<slug>/rehearsal/chords")
def rehearsal_chords(slug: str):
    song = _load_song(slug)
    if song is None:
        return "Chanson introuvable.", 404
    sections_by_id = {s["id"]: s for s in song.get("sections", [])}
    structure_items = [
        sid for sid in song.get("structure_sequence", [])
        if isinstance(sid, str) and not sid.startswith("_comment")
    ]
    return render_template("rehearsal_chords.html", song=song, slug=slug,
                           sections_by_id=sections_by_id,
                           structure_items=structure_items)


@app.route("/song/<slug>/rehearsal/memo")
def rehearsal_memo(slug: str):
    song = _load_song(slug)
    if song is None:
        return "Chanson introuvable.", 404
    memo_lines = build_memo_lines(song)
    return render_template("rehearsal_memo.html", song=song, slug=slug,
                           memo_lines=memo_lines)


@app.route("/song/<slug>/review-status", methods=["POST"])
def update_review_status(slug: str):
    song = _load_song(slug)
    if song is None:
        return jsonify(error="Chanson introuvable"), 404
    status = request.form.get("status", "").strip()
    if status not in ("ok", "to_review", "draft", ""):
        return jsonify(error="Statut invalide"), 400
    if status:
        song["review_status"] = status
    else:
        song.pop("review_status", None)
    _save_song(slug, song)
    return jsonify(ok=True, status=status)


@app.route("/song/<slug>/transpose", methods=["POST"])
def transpose_route(slug: str):
    song = _load_song(slug)
    if song is None:
        return jsonify(error="Chanson introuvable"), 404
    try:
        semitones = int(request.form.get("semitones", 0))
    except (ValueError, TypeError):
        return jsonify(error="Valeur invalide"), 400
    if semitones == 0:
        return jsonify(error="0 demi-ton — aucun changement"), 400
    if not (-11 <= semitones <= 11):
        return jsonify(error="Valeur hors limites (−11 à +11)"), 400
    song = _do_transpose(song, semitones)
    errors = validate_song_json(song)
    if errors:
        return jsonify(error=errors[0]), 400
    _save_song(slug, song)
    return jsonify(ok=True, key=song.get("meta", {}).get("key", ""))


@app.route("/song/<slug>/download-json")
def download_json(slug: str):
    from flask import send_file
    from io import BytesIO
    song = _load_song(slug)
    if song is None:
        return "Fichier introuvable.", 404
    data = json.dumps(song, ensure_ascii=False, indent=2).encode("utf-8")
    return send_file(
        BytesIO(data),
        as_attachment=True,
        download_name=f"song_{slug}.json",
        mimetype="application/json",
    )


# ---------------------------------------------------------------------------
# Lancement
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import threading
    import webbrowser

    from config import OUTPUT_DIR
    from storage import get_storage as _gs

    st = _gs()
    if STORAGE_BACKEND == "local":
        from config import DATA_DIR, PDF_EXPORT_DIR as _EXP
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        print("Chords — interface web locale")
        print(f"  data/   : {DATA_DIR}")
        print(f"  output/ : {OUTPUT_DIR}")
        print(f"  export/ : {_EXP}")
    else:
        print("Chords — interface web (Supabase)")
        print(f"  backend : {STORAGE_BACKEND}")
    print()

    threading.Timer(1.0, lambda: webbrowser.open("http://localhost:5000")).start()
    app.run(debug=False, port=5000)
