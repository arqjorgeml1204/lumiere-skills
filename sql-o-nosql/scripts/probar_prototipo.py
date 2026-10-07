"""probar_prototipo.py — carga prototipo.sql en una base SQLite, ejecuta sus consultas clave y prueba sus reglas.

Uso:  python probar_prototipo.py [prototipo.sql]
- Crea (o recrea) prototipo.db junto al archivo .sql.
- Ejecuta el esquema y los datos de ejemplo (todo lo que va antes del primer marcador).
- «-- consulta: <nombre>»: ejecuta la consulta y muestra sus resultados.
- «-- debe-fallar: <nombre>»: una regla de negocio que la base debe rechazar (cupo lleno, monto negativo,
  referencia inexistente…). Comprueba que SÍ falla y la deshace; si la base la acepta, cuenta como error.
- Termina con código 1 si algo falla, para corregir antes de entregar.
Solo usa la biblioteca estándar de Python (sqlite3).
"""
import os
import re
import sqlite3
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # acentos correctos en la consola de Windows

ruta_sql = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "prototipo.sql")
ruta_db = os.path.splitext(ruta_sql)[0] + ".db"
texto = open(ruta_sql, encoding="utf-8").read()

# Separa el script en el bloque inicial (esquema + datos) y los bloques marcados.
partes = re.split(r"^--\s*(consulta|debe-fallar):\s*(.+)$", texto, flags=re.MULTILINE)
inicio = partes[0]
bloques = [(partes[i], partes[i + 1].strip(), partes[i + 2].strip()) for i in range(1, len(partes), 3)]
consultas = [(n, s) for tipo, n, s in bloques if tipo == "consulta" and s]
negativas = [(n, s) for tipo, n, s in bloques if tipo == "debe-fallar" and s]

if os.path.exists(ruta_db):
    os.remove(ruta_db)
db = sqlite3.connect(ruta_db, isolation_level=None)  # control explícito de transacciones
db.execute("PRAGMA foreign_keys = ON")
errores = 0
try:
    db.executescript(inicio)
except sqlite3.Error as e:
    print(f"ERROR en esquema o datos: {e}")
    sys.exit(1)

tablas = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
print(f"Base creada: {ruta_db}")
for t in tablas:
    n = db.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
    print(f"  {t}: {n} filas")

for nombre, sql in consultas:
    print(f"\n== {nombre}")
    try:
        cur = db.execute(sql.rstrip(";"))
        columnas = [c[0] for c in cur.description] if cur.description else []
        filas = cur.fetchall()
        if columnas:
            print("  " + " | ".join(columnas))
        for f in filas[:10]:
            print("  " + " | ".join("" if v is None else str(v) for v in f))
        if len(filas) > 10:
            print(f"  … {len(filas) - 10} filas más")
        if not filas:
            print("  (sin resultados: revisa los datos de ejemplo)")
    except sqlite3.Error as e:
        errores += 1
        print(f"  ERROR: {e}")

for nombre, sql in negativas:
    db.execute("BEGIN")
    try:
        for sentencia in [s for s in sql.split(";") if s.strip()]:
            db.execute(sentencia)
        errores += 1
        print(f"\nERROR: «{nombre}» debía fallar y la base lo aceptó")
    except sqlite3.Error as e:
        print(f"\n== debe fallar: {nombre} → rechazado ✓ ({e})")
    finally:
        db.execute("ROLLBACK")

# Integridad referencial: no debe haber filas huérfanas.
huerfanas = db.execute("PRAGMA foreign_key_check").fetchall()
if huerfanas:
    errores += 1
    print(f"\nERROR: {len(huerfanas)} filas violan claves foráneas: {huerfanas[:5]}")

print(f"\n{'OK' if not errores else 'CON ERRORES'}: {len(consultas)} consultas, {len(negativas)} reglas probadas, {errores} error(es).")
sys.exit(1 if errores else 0)
