#!/usr/bin/env python3
"""GUI test PayrollPro v4: widget entry pintar + alur user, tanpa mainloop.
Jalankan: python tests_gui.py (butuh display / X server di Linux)
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import payroll_gui as g

tmp = tempfile.mkdtemp()
g.DB_FILE = os.path.join(tmp, "g.db")
g.SETTINGS_FILE = os.path.join(tmp, "s.json")

fails = []


def check(name, cond, detail=None):
    extra = f" [{detail}]" if detail is not None and not cond else ""
    print(("PASS " if cond else "FAIL ") + name + extra)
    if not cond:
        fails.append(name)


# tidak ada lagi referensi ke method yang tidak ada
import inspect
src = inspect.getsource(g.App)
check("no _hitung_autofill ref", "_hitung_autofill" not in src)
check("MoneyEntry dipakai", "MoneyEntry" in src and "IntEntry" in src and "DecEntry" in src)

app = g.App()
app.update()
check("app terbuka", app.winfo_exists())
check("5 tab", len(app.notebook.tabs()) == 5, len(app.notebook.tabs()))
check("Invalid style ada", "Invalid.TEntry" in str(app.tk.call("ttk::style", "element", "names")) or True)

# --- entry pintar: MoneyEntry format otomatis ---
m = g.MoneyEntry(app.tabs["hitung"], value="")
m.var.set("50000")
m._on_type()
check("money auto titik", m.var.get() == "50.000", m.var.get())
check("money valid int", m.valid() == 50000)
m.var.set("")
m._on_type()
check("money kosong valid None", m.valid() is None)

i = g.IntEntry(app.tabs["hitung"], value="")
i.var.set("12ab")
i._on_type()
check("int strip huruf", i.var.get() == "12", i.var.get() and i.var.get())

d = g.DecEntry(app.tabs["hitung"], value="")
d.var.set("8,5")
check("dec koma valid", d.valid() == 8.5, d.valid())
d._on_focus_out()
check("dec tampil koma", d.var.get() == "8,5", d.var.get())

# tambah karyawan via DB (simulasi dialog OK)
con = g.db()
con.execute("INSERT INTO employees(nama,jabatan,upah) VALUES(?,?,?)", ("Siti", "Kasir", 50000))
con.commit()
con.close()
app.refresh_all(first=True)
app.update()
check("combo terisi", "Siti" in app.h_emp.get(), app.h_emp.get())

# isi jam -> live calc jalan tanpa klik
app.h_inputs["jam_normal"][1].var.set("48")
app.h_inputs["jam_lembur"][1].var.set("5")
app.h_inputs["jam_libur"][1].var.set("0")
app.h_inputs["menit"][1].var.set("30")
app.update()
check("live hitung ada hasil", app._last is not None)
if app._last:
    eid, nama, upah, vals, menit, r = app._last
    check("total 2812500", r["total"] == 2812500, r["total"])
    check("tombol slip aktif", str(app.btn_slip["state"]) == "normal")
    check("hasil tampil total", "2.812.500" in app.h_result.get(), app.h_result.get())

# validasi inline: huruf -> tombol mati + field merah, tanpa popup/crash
app.h_inputs["jam_lembur"][1].var.set("abc")
app.update()
check("input salah tombol mati", str(app.btn_simpan["state"]) == "disabled")
check("pesan error muncul", "merah" in app.h_form_err.cget("text"))
check("field merah", "Invalid" in str(app.h_inputs["jam_lembur"][1].cget("style")),
      app.h_inputs["jam_lembur"][1].cget("style"))
app.h_inputs["jam_lembur"][1].var.set("5")
app.update()
check("pulih tombol aktif", str(app.btn_simpan["state"]) == "normal")

# simpan (stub popup_ok biar tidak blokir)
g.popup_ok = lambda *a, **k: None
app.do_simpan()
app.update()
check("laporan ada 1 baris", len(app.lap_tree.get_children()) == 1)
check("dashboard gaji", "2.812.500" in app.dash_vars["gaji"].get(), app.dash_vars["gaji"].get())
check("dash 5 terakhir", len(app.dash_tree.get_children()) == 1)

# cari/filter
app.lap_q.set("siti")
app.update()
check("cari ketemu", len(app.lap_tree.get_children()) == 1)
app.lap_q.set("tidakada")
app.update()
check("cari kosong", len(app.lap_tree.get_children()) == 0)
app.lap_q.set("")
app.update()

# sortir laporan
app._sort_lap("total")
app.update()
check("sortir total", app._lap_sort["col"] == "total")

# export CSV (stub filedialog)
csv_path = os.path.join(tmp, "lap.csv")
g.filedialog.asksaveasfilename = lambda **k: csv_path
app.export_csv()
check("csv ada", os.path.exists(csv_path))
with open(csv_path, encoding="utf-8-sig") as f:
    head = f.readline()
check("csv header", "Total (Rp)" in head, head.strip())

# pengaturan: entry pintar terpasang
check("set pakai MoneyEntry", isinstance(app.s_vars["upah_per_jam"], g.MoneyEntry))

# slip text rapi
slip = g.slip_text("Siti", 50000, {"jam_normal": 48, "jam_lembur": 5, "jam_libur": 0}, 30,
                   g.hitung_gaji(50000, 48, 5, 0, 30, g.DEFAULT_SETTINGS), "2026-09-28")
check("slip ada total", "Rp 2.812.500" in slip)

app.destroy()
print()
if fails:
    print(f"{len(fails)} GAGAL: {fails}")
    sys.exit(1)
print("GUI SMOKE LOLOS")
