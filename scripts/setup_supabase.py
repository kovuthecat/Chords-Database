"""
Initialisation Supabase : applique le schéma SQL et crée le bucket Storage.
Usage : python scripts/setup_supabase.py
"""
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR / "scripts"))


def _load_env() -> None:
    env_path = ROOT_DIR / ".env.local"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def apply_schema(url: str, key: str, schema_sql: str) -> bool:
    """Applique le schéma via l'endpoint REST /rest/v1/rpc ou fallback httpx."""
    import httpx

    # Supabase expose /rest/v1/rpc pour les fonctions SQL.
    # Pour du DDL brut, on passe par l'endpoint interne /pg/query (dashboard API).
    # Avec le service_role_key, on peut aussi utiliser /rest/v1/ avec Prefer: resolution=merge-duplicates.
    # La méthode la plus fiable : POST sur /rest/v1/rpc avec une fonction exec_sql si elle existe,
    # sinon on crée les tables directement via l'API postgrest-admin.

    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }

    # Tentative 1 : /pg/query (endpoint interne Supabase v2)
    try:
        resp = httpx.post(
            f"{url}/pg/query",
            headers=headers,
            json={"query": schema_sql},
            timeout=30,
        )
        if resp.status_code < 300:
            print("  ✓ Schéma appliqué via /pg/query")
            return True
        # Not available — try next method
    except Exception:
        pass

    # Tentative 2 : /rest/v1/rpc/exec_sql (si la fonction existe)
    try:
        # Envoyer instruction par instruction
        statements = [s.strip() for s in schema_sql.split(";") if s.strip() and not s.strip().startswith("--")]
        for stmt in statements:
            resp = httpx.post(
                f"{url}/rest/v1/rpc/exec_sql",
                headers=headers,
                json={"sql": stmt + ";"},
                timeout=30,
            )
            if resp.status_code >= 400 and "does not exist" not in resp.text:
                pass  # ignore errors for idempotent statements
        print("  ~ /rest/v1/rpc/exec_sql tenté (résultat non garanti)")
        return False
    except Exception:
        pass

    return False


def check_tables(url: str, key: str) -> dict[str, bool]:
    import httpx
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
    }
    results = {}
    for table in ("songs", "song_backups"):
        try:
            resp = httpx.get(
                f"{url}/rest/v1/{table}?limit=0",
                headers=headers,
                timeout=10,
            )
            results[table] = resp.status_code == 200
        except Exception:
            results[table] = False
    return results


def create_bucket(url: str, key: str, bucket: str) -> bool:
    from supabase import create_client
    client = create_client(url, key)
    try:
        existing = [b.name for b in client.storage.list_buckets()]
        if bucket in existing:
            print(f"  [OK] Bucket '{bucket}' existe deja")
            return True
        client.storage.create_bucket(bucket, options={"public": True})
        print(f"  [OK] Bucket '{bucket}' cree (public=true)")
        return True
    except Exception as e:
        print(f"  [ERR] Bucket : {e}")
        return False


def main() -> None:
    _load_env()
    url    = os.environ.get("SUPABASE_URL", "")
    key    = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    bucket = os.environ.get("SUPABASE_STORAGE_BUCKET", "chords-exports")

    if not url or not key:
        print("ERREUR : SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY manquants dans .env.local")
        sys.exit(1)

    print(f"\n{'='*55}")
    print(f"  Setup Supabase")
    print(f"{'='*55}\n")

    # 1. Verification tables actuelles
    print("-- 1. Tables existantes")
    tables = check_tables(url, key)
    for t, ok in tables.items():
        status = "OK" if ok else "ABSENT"
        print(f"  [{status}] {t}")

    # 2. Application du schema si tables absentes
    if not all(tables.values()):
        print("\n-- 2. Application du schema SQL")
        schema_path = ROOT_DIR / "supabase" / "schema.sql"
        schema_sql  = schema_path.read_text(encoding="utf-8")
        ok = apply_schema(url, key, schema_sql)
        if not ok:
            print()
            print("  ATTENTION : application automatique impossible")
            print("  (DDL requiert un acces direct Postgres, pas disponible via REST).")
            print()
            print("  ACTION REQUISE -> Coller dans Supabase SQL Editor :")
            print("    https://supabase.com/dashboard/project/jfmlcxrlubtqyxpspknx/sql/new")
            print("    Fichier : supabase/schema.sql")
            print()
            print("  Apres avoir applique le schema, relancez ce script.")
            print()
    else:
        print("\n-- 2. Schema")
        print("  [OK] Tables deja presentes")

    # 3. Bucket Storage
    print("\n-- 3. Bucket Storage")
    create_bucket(url, key, bucket)

    # 4. Resume
    tables2 = check_tables(url, key)
    print("\n-- Resume")
    for t, ok in tables2.items():
        status = "OK" if ok else "ABSENT"
        print(f"  [{status}] Table {t}")
    pret = all(tables2.values())
    print(f"  Pret pour migration : {pret}")
    print(f"{'='*55}\n")

    if not pret:
        sys.exit(1)


if __name__ == "__main__":
    main()
