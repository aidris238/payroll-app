#!/usr/bin/env python3
"""Smoke test logika PayrollPro v3 — tanpa GUI (tanpa display).
Jalankan: python tests_smoke.py
Lolos = semua assert + DB roundtrip OK.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import payroll_gui as g

fails = []


def check(name, cond, detail=None):
    extra = ""
    if detail is not None and not cond:
        extra = f" [{detail}]"
    print(("PASS " if cond else "FAIL ") + name + extra)
    if not cond:
        fails.append(name)


# 1. rumus dasar: 48 jam normal @50rb, tanpa lembur
s = dict(g.DEFAULT_SETTINGS)
r = g.hitung_gaji(50000, 48, 0, 0, 0, s)
check("pokok 48x50rb", r["pokok"] == 2400000, r)
check("total tanpa lembur", r["total"] == 2400000, r)

# 2. lembur 5 jam @1.5x = 375rb
r = g.hitung_gaji(50000, 48, 5, 0, 0, s)
check("lembur 5 jam", r["lembur"] == 5 * 50000 * 1.5, r)
check("total 2775000", r["total"] == 2400000 + 375000, r)

# 3. menit 30 -> 0.5 jam lembur = 37500
r = g.hitung_gaji(50000, 48, 0, 0, 30, s)
check("menit 30", abs(r["menit_jam"] - 0.5) < 1e-9, r)
check("lembur dari menit", r["lembur"] == 0.5 * 50000 * 1.5, r)

# 4. jam normal berlebih 50 (>48) -> 2 jam jadi lembur
r = g.hitung_gaji(50000, 50, 0, 0, 0, s)
check("normal dibayar max 48", r["normal_dibayar"] == 48, r)
check("lebih 2 jam lembur", abs(r["jam_lembur_total"] - 2.0) < 1e-9, r)

# 5. libur 4 jam @2x = 400rb
r = g.hitung_gaji(50000, 48, 0, 4, 0, s)
check("libur 4 jam", r["libur"] == 4 * 50000 * 2.0, r)

# 6. pembulatan menit
check("bulat 0", g.bulatkan_menit(0) == 0.0)
check("bulat 1 mnt->0.25j", abs(g.bulatkan_menit(1) - 0.25) < 1e-9)
check("bulat 16 mnt->0.5j", abs(g.bulatkan_menit(16) - 0.5) < 1e-9)

# 7. parse angka
check("parse 50.000", g.parse_angka("50.000") == 50000)
check("parse 8,5", g.parse_angka("8,5") == 8.5)
check("parse huruf", g.parse_angka("abc") is None)
check("parse kosong", g.parse_angka("") is None)

# 8. rupiah
check("rupiah", g.rupiah(2812500) == "Rp 2.812.500", g.rupiah(2812500))

# 9. DB roundtrip di temp dir
tmp = tempfile.mkdtemp()
old_db, old_set = g.DB_FILE, g.SETTINGS_FILE
g.DB_FILE = os.path.join(tmp, "t.db")
g.SETTINGS_FILE = os.path.join(tmp, "s.json")
try:
    con = g.db()
    con.execute("INSERT INTO employees(nama,jabatan,upah) VALUES(?,?,?)", ("Budi", "Staff", 50000))
    con.commit()
    rows = con.execute("SELECT nama,upah FROM employees WHERE aktif=1").fetchall()
    check("db insert/select", rows == [("Budi", 50000.0)], rows)
    con.execute("INSERT INTO records(employee_id,tanggal,jam_normal,jam_lembur,jam_libur,menit,total)"
                " VALUES(?,?,?,?,?,?,?)", (1, "2026-09-28", 48, 5, 0, 30, 2812500))
    con.commit()
    n = con.execute("SELECT COUNT(*) FROM records").fetchone()[0]
    check("db record", n == 1, n)
    con.close()
    g.save_settings(s)
    check("settings roundtrip", g.load_settings() == s, g.load_settings())
finally:
    g.DB_FILE, g.SETTINGS_FILE = old_db, old_set

print()
if fails:
    print(f"{len(fails)} GAGAL: {fails}")
    sys.exit(1)
print("SEMUA LOLOS")
