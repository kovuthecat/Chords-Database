"""
Collecte multi-sources pour un fichier song JSON.

Modes d'utilisation :

  Init (crée le JSON + affiche les requêtes de recherche) :
    python scripts/collect.py "Titre" "Artiste"
    python scripts/collect.py "Titre" "Artiste" --slug mon-slug-custom

  Ingérer une source (texte brut collé ou fourni via stdin) :
    python scripts/collect.py data/song_<slug>.json --ingest "Ultimate Guitar"
    python scripts/collect.py data/song_<slug>.json --ingest "Ultimate Guitar" --file raw.txt

  Voir le statut de collecte :
    python scripts/collect.py data/song_<slug>.json --status
"""

import io
import json
import re
import sys
from datetime import datetime
from pathlib import Path


def _ensure_utf8():
    if hasattr(sys.stdout, "buffer") and getattr(sys.stdout, "encoding", "").lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Reconnaissance des accords
# ---------------------------------------------------------------------------

CHORD_RE = re.compile(
    r'^[A-G]'                           # note racine
    r'[b#]?'                            # altération
    r'(?:m(?:aj)?|min|aug|dim|sus)?'    # qualité
    r'(?:\d+)?'                         # chiffre (7, 9, 11…)
    r'(?:[b#]\d+)?'                     # altération d'extension (b5, #11, etc.)
    r'(?:add\d+)?'                      # extension add
    r'(?:sus\d+)?'                      # suspension
    r'(?:/(?:[A-G][b#]?|\d+))?$'       # basse (note ou chiffre, ex: Am7/4, C/G)
)

def is_chord(token: str) -> bool:
    return bool(CHORD_RE.match(token.strip("()[]")))

def is_chord_line(line: str) -> bool:
    tokens = line.split()
    if not tokens:
        return False
    chord_count = sum(1 for t in tokens if is_chord(t))
    return chord_count >= 1 and chord_count / len(tokens) >= 0.55

def is_chord_grid(line: str) -> bool:
    return bool(re.search(r'\|.+\|', line))

def extract_chords_from_line(line: str) -> list[dict]:
    """Retourne [{chord, position}] depuis une ligne d'accords."""
    result = []
    for m in re.finditer(r'\S+', line):
        token = m.group().strip("()[]")
        if is_chord(token):
            result.append({"chord": token, "position": m.start()})
    return result


# ---------------------------------------------------------------------------
# Reconnaissance des sections
# ---------------------------------------------------------------------------

SECTION_MAP = [
    (re.compile(r'intro', re.I),                           "intro",       "Intro"),
    (re.compile(r'verse|couplet|v(?:erse)?\s*\d', re.I),  "verse",       "Couplet"),
    (re.compile(r'pre.?chorus|pré.?refrain', re.I),        "pre_chorus",  "Pré-refrain"),
    (re.compile(r'chorus|refrain', re.I),                  "chorus",      "Refrain"),
    (re.compile(r'bridge|pont', re.I),                     "bridge",      "Pont"),
    (re.compile(r'solo', re.I),                            "solo",        "Solo"),
    (re.compile(r'interlude|instrumental', re.I),          "interlude",   "Interlude"),
    (re.compile(r'outro|fin\b', re.I),                     "outro",       "Outro"),
    (re.compile(r'breakdown', re.I),                       "breakdown",   "Breakdown"),
]

METADATA_LINE_RE = re.compile(
    r'^\s*(?:capo|key|tonali(?:té|te)|tempo|time[\s_]?signature|tuning|accordage|bpm)\s*[:\s]',
    re.IGNORECASE,
)

SECTION_LINE_RE = re.compile(
    r'^\s*[\[\(]?'
    r'(intro|verse|couplet|pre.?chorus|pré.?refrain|chorus|refrain|bridge|pont|solo|interlude|instrumental|outro|fin|breakdown|v\.\s*\d)'
    r'[\s\d:.\]\)]*$',
    re.IGNORECASE,
)

def detect_section_type(line: str) -> tuple[str, str] | None:
    """Retourne (type, label_fr) si la ligne est un titre de section."""
    stripped = line.strip()
    if not SECTION_LINE_RE.match(stripped):
        return None
    clean = re.sub(r'[\[\]():]', '', stripped).strip()
    for pattern, stype, default_label in SECTION_MAP:
        if pattern.search(clean):
            num_match = re.search(r'\d+', clean)
            label = default_label + (f" {num_match.group()}" if num_match else "")
            return stype, label
    return None

def detect_repeat(line: str) -> int | None:
    """Retourne le nombre de répétitions si la ligne l'indique."""
    m = re.search(r'[x×]\s*(\d+)', line.strip(), re.IGNORECASE)
    if m:
        return int(m.group(1))
    return None


# ---------------------------------------------------------------------------
# Parseur de texte brut chord
# ---------------------------------------------------------------------------

def parse_raw_text(text: str) -> dict:
    """
    Parse du texte brut au format chord (copié-collé depuis une source).
    Retourne un dict partiel : {key, capo, sections, chords_used}.
    """
    lines = text.splitlines()
    sections = []
    chords_used_set: set[str] = set()

    current_type = "verse"
    current_label = "Couplet"
    current_lines = []
    current_is_instr = False
    current_chord_grid = None
    current_repeats = 1
    section_counter: dict[str, int] = {}
    section_started = False  # True dès qu'on a vu un en-tête de section explicite

    def _flush_section():
        nonlocal current_lines, current_is_instr, current_chord_grid, current_repeats
        if not current_lines and not current_chord_grid:
            return
        if not section_started:
            # Lignes orphelines avant le premier en-tête : on ignore
            current_lines.clear()
            current_chord_grid = None
            return

        stype = current_type
        section_counter[stype] = section_counter.get(stype, 0) + 1
        idx = section_counter[stype]
        sid = f"{stype}_{idx}"

        section = {
            "id": sid,
            "type": stype,
            "label": current_label,
            "is_instrumental": current_is_instr,
            "chord_grid": current_chord_grid,
            "repeats": current_repeats,
            "bars": None,
            "lines": current_lines[:],
            "confidence": 0.75,
            "source_agreement": 0.0,
        }
        sections.append(section)
        current_lines.clear()
        current_chord_grid = None
        current_is_instr = False
        current_repeats = 1

    # Extraction capo depuis l'en-tête
    capo = 0
    raw_key = None
    for line in lines[:15]:
        m = re.search(r'capo\s*[:\s]?\s*(\d+)', line, re.IGNORECASE)
        if m:
            capo = int(m.group(1))
        m = re.search(r'key\s*[:\s]?\s*([A-G][b#]?m?)', line, re.IGNORECASE)
        if m and not raw_key:
            raw_key = m.group(1)
        m = re.search(r'tonali(?:té|te)\s*[:\s]?\s*([A-G][b#]?m?)', line, re.IGNORECASE)
        if m and not raw_key:
            raw_key = m.group(1)

    # Parsing ligne par ligne
    pending_chords: list[dict] | None = None

    for line in lines:
        stripped = line.strip()

        # Ignorer lignes métadonnées (Capo:, Key:, Tuning:, etc.)
        if METADATA_LINE_RE.match(stripped):
            continue

        # Ligne vide : sépare les sections implicites si on a accumulé du contenu
        if not stripped:
            if pending_chords is not None:
                # Ligne d'accords sans paroles associées → ligne instrumentale orpheline
                current_lines.append({"chords": pending_chords, "lyrics": ""})
                for c in pending_chords:
                    chords_used_set.add(c["chord"])
                pending_chords = None
            continue

        # Indicateur de répétition (x2, ×3, etc.)
        repeats = detect_repeat(stripped)
        if repeats is not None and len(stripped) < 6:
            # Applique à la section en cours (pas encore flushée)
            current_repeats = repeats
            continue

        # En-tête de section
        section_info = detect_section_type(stripped)
        if section_info:
            _flush_section()
            if pending_chords:
                pending_chords = None
            current_type, current_label = section_info
            current_is_instr = current_type in ("intro", "interlude", "solo")
            section_started = True
            continue

        # Grille d'accords (| Am | F | C | G |)
        if is_chord_grid(stripped):
            if pending_chords is not None:
                current_lines.append({"chords": pending_chords, "lyrics": ""})
                for c in pending_chords:
                    chords_used_set.add(c["chord"])
                pending_chords = None
            # Concaténer les lignes multiples avec \n
            if current_chord_grid:
                current_chord_grid += "\n" + stripped
            else:
                current_chord_grid = stripped
            for token in re.sub(r'[|]', ' ', stripped).split():
                if is_chord(token):
                    chords_used_set.add(token)
            current_is_instr = True
            continue

        # Ligne d'accords
        if is_chord_line(stripped):
            if pending_chords is not None:
                # Deux lignes d'accords consécutives → flush la première sans paroles
                current_lines.append({"chords": pending_chords, "lyrics": ""})
                for c in pending_chords:
                    chords_used_set.add(c["chord"])
            pending_chords = extract_chords_from_line(line)
            continue

        # Ligne de paroles
        if pending_chords is not None:
            current_lines.append({"chords": pending_chords, "lyrics": stripped})
            for c in pending_chords:
                chords_used_set.add(c["chord"])
            pending_chords = None
        else:
            # Paroles sans accords
            current_lines.append({"chords": [], "lyrics": stripped})

    # Flush final
    if pending_chords is not None:
        current_lines.append({"chords": pending_chords, "lyrics": ""})
        for c in pending_chords:
            chords_used_set.add(c["chord"])
    _flush_section()

    return {
        "key": raw_key,
        "capo": capo,
        "sections": sections,
        "chords_used": sorted(chords_used_set),
    }


# ---------------------------------------------------------------------------
# Initialisation du JSON
# ---------------------------------------------------------------------------

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[àáâã]', 'a', text)
    text = re.sub(r'[éèêë]', 'e', text)
    text = re.sub(r'[îï]', 'i', text)
    text = re.sub(r'[ôö]', 'o', text)
    text = re.sub(r'[ùûü]', 'u', text)
    text = re.sub(r'[ç]', 'c', text)
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')


def init_song(title: str, artist: str, slug: str | None = None) -> tuple[Path, dict]:
    slug = slug or f"{slugify(artist)}-{slugify(title)}"
    json_path = Path("data") / f"song_{slug}.json"

    if json_path.exists():
        print(f"Le fichier {json_path} existe déjà. Utilise --status pour voir l'état.")
        sys.exit(1)

    song = {
        "meta": {
            "title": title,
            "artist": artist,
            "key": None,
            "key_mode": None,
            "capo": 0,
            "tempo": None,
            "time_signature": "4/4",
            "tuning": "standard",
            "version": "studio",
            "slug": slug,
            "generated_at": datetime.now().isoformat(),
        },
        "chords_used": [],
        "sources": [],
        "sections": [],
        "structure_sequence": [],
        "confidence": {
            "overall": 0.0,
            "structure": 0.0,
            "chords": 0.0,
            "capo": 0.0,
            "instrumental_sections": 0.0,
            "lyric_alignment": 0.0,
        },
        "warnings": [],
        "variants": [],
        "validation": {
            "status": "pending",
            "validated_at": None,
            "user_corrections": [],
        },
        "_collection_status": "initialized",
    }

    json_path.parent.mkdir(exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(song, f, ensure_ascii=False, indent=2)

    return json_path, song


def print_search_queries(title: str, artist: str):
    q = f'"{title}" {artist} chords'
    q_fr = f'"{title}" {artist} accords guitare'

    print()
    print("REQUÊTES DE RECHERCHE SUGGÉRÉES")
    print("─" * 56)
    print()
    print("  Ultimate Guitar :")
    print(f"    {q} site:ultimate-guitar.com")
    print()
    print("  La Boîte à Musique :")
    print(f"    {q_fr} site:boiteamusique.com")
    print()
    print("  Songsterr :")
    print(f"    {q} site:songsterr.com")
    print()
    print("  Recherche générale :")
    print(f"    {q}")
    print(f"    {q_fr}")
    print()
    print("ÉTAPES SUIVANTES")
    print("─" * 56)
    print("  1. Lancer ces requêtes avec WebSearch.")
    print("  2. Récupérer le contenu textuel des 2-3 meilleures pages")
    print("     (WebFetch ou copier-coller le texte chord).")
    print("  3. Injecter chaque source :")
    print(f"     python scripts/collect.py data/song_<slug>.json --ingest \"Nom source\"")
    print()


# ---------------------------------------------------------------------------
# Ingestion d'une source
# ---------------------------------------------------------------------------

def ingest_source(json_path: str, source_name: str, raw_text: str):
    path = Path(json_path)
    with open(path, encoding="utf-8") as f:
        song = json.load(f)

    parsed = parse_raw_text(raw_text)

    source_entry = {
        "name": source_name,
        "url": "",
        "key": parsed.get("key"),
        "capo": parsed.get("capo", 0),
        "chord_set": parsed.get("chords_used", []),
        "collected_at": datetime.now().isoformat(),
        "notes": f"{len(parsed['sections'])} sections détectées",
    }
    song["sources"].append(source_entry)

    # Merge sections : si c'est la première source, on prend tel quel
    if not song["sections"]:
        song["sections"] = parsed["sections"]
        song["structure_sequence"] = [s["id"] for s in parsed["sections"]]
        if parsed.get("key"):
            raw_key = parsed["key"]
            m_key = re.match(r'([A-G][b#]?)(m(?:in)?)?', raw_key, re.IGNORECASE)
            if m_key:
                song["meta"]["key"] = m_key.group(1)
                song["meta"]["key_mode"] = "minor" if m_key.group(2) else "major"
            else:
                song["meta"]["key"] = raw_key
        if parsed.get("capo"):
            song["meta"]["capo"] = parsed["capo"]
    else:
        # Sources supplémentaires : on les ajoute en suffixant les IDs
        suffix = f"_s{len(song['sources'])}"
        for s in parsed["sections"]:
            s["id"] = s["id"] + suffix
        song["sections"].extend(parsed["sections"])

    # Mise à jour des accords utilisés
    all_chords = set(song.get("chords_used", []))
    all_chords.update(parsed.get("chords_used", []))
    song["chords_used"] = sorted(all_chords)

    song["_collection_status"] = f"{len(song['sources'])} source(s) collectée(s)"

    with open(path, "w", encoding="utf-8") as f:
        json.dump(song, f, ensure_ascii=False, indent=2)

    print(f"\n  Source '{source_name}' ingérée dans {json_path}")
    print(f"  Sections détectées   : {len(parsed['sections'])}")
    print(f"  Accords trouvés      : {' '.join(parsed['chords_used'])}")
    if parsed.get("key"):
        print(f"  Tonalité détectée    : {parsed['key']}")
    if parsed.get("capo"):
        print(f"  Capo détecté         : {parsed['capo']}")
    print(f"  Sources totales      : {len(song['sources'])}")
    print()
    if len(song["sources"]) < 2:
        print("  → Ajoute une deuxième source pour le croisement.")
        print(f"    python scripts/collect.py {json_path} --ingest \"Autre Source\"")
    else:
        print("  → Tu peux maintenant valider :")
        print(f"    python scripts/display_validation.py {json_path}")
    print()


# ---------------------------------------------------------------------------
# Statut de collecte
# ---------------------------------------------------------------------------

def print_status(json_path: str):
    path = Path(json_path)
    with open(path, encoding="utf-8") as f:
        song = json.load(f)

    meta = song["meta"]
    sources = song.get("sources", [])
    sections = song.get("sections", [])
    val_status = song.get("validation", {}).get("status", "pending")

    print()
    print(f"  Titre    : {meta.get('title')} — {meta.get('artist')}")
    print(f"  Slug     : {meta.get('slug')}")
    print(f"  Statut   : {song.get('_collection_status', '?')}")
    print(f"  Validation : {val_status}")
    print()
    print(f"  Sources ({len(sources)}) :")
    for s in sources:
        chords = ' '.join(s.get('chord_set', [])[:6])
        print(f"    • {s['name']} — {s.get('notes', '')} — accords : {chords}…")
    print()
    print(f"  Sections ({len(sections)}) :")
    for s in sections:
        tag = " [instr]" if s.get("is_instrumental") else ""
        print(f"    • {s['id']} — {s['label']}{tag} — {len(s.get('lines', []))} lignes")
    print()
    if len(sources) < 2:
        print("  ⚠  Moins de 2 sources — confiance limitée.")
    if val_status == "user_validated":
        print("  ✓  Validé. Lance : python scripts/generate_docx.py " + json_path)
    elif len(sources) >= 1:
        print("  → Valider : python scripts/display_validation.py " + json_path)
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    _ensure_utf8()
    args = sys.argv[1:]

    if not args:
        print(__doc__)
        sys.exit(0)

    # Mode status
    if len(args) == 2 and args[1] == "--status":
        print_status(args[0])
        return

    # Mode ingest
    if "--ingest" in args:
        idx = args.index("--ingest")
        json_path = args[0]
        source_name = args[idx + 1] if idx + 1 < len(args) else "Source inconnue"

        file_flag = "--file"
        if file_flag in args:
            file_idx = args.index(file_flag)
            file_path = args[file_idx + 1]
            with open(file_path, encoding="utf-8") as f:
                raw_text = f.read()
        else:
            print(f"  Colle le texte brut de la source '{source_name}'.")
            print("  Termine par une ligne contenant uniquement '---' puis Entrée.\n")
            lines = []
            try:
                while True:
                    line = input()
                    if line.strip() == "---":
                        break
                    lines.append(line)
            except EOFError:
                pass
            raw_text = "\n".join(lines)

        ingest_source(json_path, source_name, raw_text)
        return

    # Mode init
    if len(args) >= 2 and not args[0].endswith(".json"):
        title = args[0]
        artist = args[1]
        slug = None
        if "--slug" in args:
            slug_idx = args.index("--slug")
            slug = args[slug_idx + 1] if slug_idx + 1 < len(args) else None

        json_path, _ = init_song(title, artist, slug)
        print(f"\n  ✓ Fichier initialisé : {json_path}")
        print_search_queries(title, artist)
        return

    print("Arguments non reconnus. Lance sans argument pour l'aide.")
    sys.exit(1)


if __name__ == "__main__":
    main()
