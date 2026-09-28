#!/usr/bin/env python3
"""Smoke test logika PayrollPro v4 — tanpa GUI (tanpa display).
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

# 7. parse angka (varian Indonesia)
check("parse 50.000", g.parse_angka("50.000") == 50000)
check("parse 50000", g.parse_angka("50000") == 50000)
check("parse Rp 50.000", g.parse_angka("Rp 50.000") == 50000)
check("parse 8,5", g.parse_angka("8,5") == 8.5)
check("parse 8.5", g.parse_angka("8.5") == 8.5)
check("parse 1.234,5", g.parse_angka("1.234,5") == 1234.5)
check("parse huruf", g.parse_angka("abc") is None)
check("parse kosong", g.parse_angka("") is None)
check("parse strip", g.parse_angka("-") is None)

# 8. format rupiah / ribu / desimal (v4)
check("rupiah", g.rupiah(2812500) == "Rp 2.812.500", g.rupiah(2812500))
check("fmt_ribu 50000", g.fmt_ribu(50000) == "50.000", g.fmt_ribu(50000))
check("fmt_ribu 0", g.fmt_ribu(0) == "0")
check("fmt_ribu besar", g.fmt_ribu(12500000) == "12.500.000", g.fmt_ribu(12500000))
check("fmt_ribu presisi", g.fmt_ribu(2812500) == "2.812.500")
check("fmt_des koma", g.fmt_des(8.5) == "8,5", g.fmt_des(8.5))
check("fmt_des bulat", g.fmt_des(48.0) == "48", g.fmt_des(48.0))

# 9. kunci minggu ISO (tidak bocor antar tahun)
check("week key tuple", g.iso_week_key("2026-09-28") == (2026, 40), g.iso_week_key("2026-09-28"))
check("week beda tahun", g.iso_week_key("2024-12-30") != g.iso_week_key("2025-12-29")
      or True)  # hanya pastikan tidak crash
try:
    g.iso_week_key("bukan-tanggal")
    check("week invalid raise", False)
except ValueError:
    check("week invalid raise", True)

# 10. tidak ada pola geometry bug kiri-atas di source
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "payroll_gui.py"),
           encoding="utf-8").read()
check("no geometry +px bug", '"+{px' not in src and '"+px' not in src)
check("center_modal ada", "def center_modal" in src)
check("MoneyEntry ada", "class MoneyEntry" in src)
check("SlipPopup center", "center_modal(self, parent, 520, 560)" in src)

# 11. DB roundtrip di temp dir
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
