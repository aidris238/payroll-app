#!/usr/bin/env python3
"""Aplikasi Penggajian Karyawan PRO - GUI Desktop Profesional.
Fitur: tab Dashboard / Karyawan / Hitung Gaji / Laporan / Pengaturan,
menu bar, database SQLite, export CSV. Stdlib only (tkinter).
"""

import csv
import json
import os
import sqlite3
import tkinter as tk
from datetime import date
from tkinter import filedialog, messagebox, ttk

APP_TITLE = "PayrollPro - Penggajian Karyawan Mingguan"
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "payroll.db")
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")

DEFAULT_SETTINGS = {
    "upah_per_jam": 50000,
    "jam_per_hari": 8.0,
    "hari_per_minggu": 6,
    "rate_lembur": 1.5,
    "rate_libur": 2.0,
    "pembulatan_menit": 15,
}

# ---------- logika hitung (murni, bisa unit-test) ----------

def bulatkan_menit(menit: int, pembulatan: int = 15) -> float:
    if menit <= 0:
        return 0.0
    return ((menit + pembulatan - 1) // pembulatan) * (pembulatan / 60)


def hitung_gaji(upah, jam_normal, jam_lembur, jam_libur, menit, s):
    jam_std = s["jam_per_hari"] * s["hari_per_minggu"]
    normal_dibayar = min(jam_normal, jam_std)
    lebih = max(0.0, jam_normal - jam_std)
    menit_jam = bulatkan_menit(menit, s["pembulatan_menit"])
    total_lembur = lebih + jam_lembur + menit_jam
    pokok = normal_dibayar * upah
    lembur = total_lembur * upah * s["rate_lembur"]
    libur = jam_libur * upah * s["rate_libur"]
    return {
        "pokok": pokok, "lembur": lembur, "libur": libur,
        "total": pokok + lembur + libur,
        "jam_lembur_total": total_lembur, "menit_jam": menit_jam,
        "normal_dibayar": normal_dibayar,
    }


def rupiah(x: float) -> str:
    return f"Rp {x:,.0f}".replace(",", ".")


# ---------- settings & db ----------

def load_settings():
    try:
        with open(SETTINGS_FILE) as f:
            d = json.load(f)
        out = dict(DEFAULT_SETTINGS)
        out.update({k: v for k, v in d.items() if k in out})
        return out
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(DEFAULT_SETTINGS)


def save_settings(s):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(s, f, indent=2)


def db():
    con = sqlite3.connect(DB_FILE)
    con.execute("""CREATE TABLE IF NOT EXISTS employees(
        id INTEGER PRIMARY KEY AUTOINCREMENT, nama TEXT NOT NULL,
        jabatan TEXT DEFAULT '', upah REAL DEFAULT 0, aktif INTEGER DEFAULT 1)""")
    con.execute("""CREATE TABLE IF NOT EXISTS records(
        id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id INTEGER,
        tanggal TEXT, jam_normal REAL, jam_lembur REAL, jam_libur REAL,
        menit INTEGER, total REAL,
        FOREIGN KEY(employee_id) REFERENCES employees(id))""")
    return con


# ---------- aplikasi ----------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("980x640")
        self.minsize(880, 560)
        self.settings = load_settings()
        self._style()
        self._menu()
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        self.tab_dash = ttk.Frame(self.notebook)
        self.tab_emp = ttk.Frame(self.notebook)
        self.tab_hitung = ttk.Frame(self.notebook)
        self.tab_lap = ttk.Frame(self.notebook)
        self.tab_set = ttk.Frame(self.notebook)
        for tab, label in [(self.tab_dash, "  Dashboard  "),
                           (self.tab_emp, "  Data Karyawan  "),
                           (self.tab_hitung, "  Hitung Gaji  "),
                           (self.tab_lap, "  Laporan  "),
                           (self.tab_set, "  Pengaturan  ")]:
            self.notebook.add(tab, text=label)
        self._build_dash()
        self._build_emp()
        self._build_hitung()
        self._build_lap()
        self._build_set()
        self.refresh_all()
        self.status = tk.StringVar(value="Siap.")
        ttk.Label(self, textvariable=self.status, style="Status.TLabel",
                  anchor="w").pack(fill="x", padx=10, pady=(0, 8))

    # ----- tampilan -----
    def _style(self):
        st = ttk.Style(self)
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        P, DARK, BG = "#2563EB", "#1E40AF", "#F1F5F9"
        self.configure(bg=BG)
        st.configure("TFrame", background=BG)
        st.configure("TLabel", background=BG, font=("Segoe UI", 10))
        st.configure("Title.TLabel", font=("Segoe UI", 16, "bold"), foreground=DARK)
        st.configure("Big.TLabel", font=("Segoe UI", 20, "bold"), foreground=DARK)
        st.configure("Card.TFrame", background="white", relief="solid", borderwidth=1)
        st.configure("Card.TLabel", background="white")
        st.configure("TButton", font=("Segoe UI", 10), padding=6)
        st.configure("Primary.TButton", background=P, foreground="white")
        st.map("Primary.TButton", background=[("active", DARK)])
        st.configure("Treeview", font=("Segoe UI", 10), rowheight=26)
        st.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        st.configure("Status.TLabel", font=("Segoe UI", 9), foreground="#475569")

    def _menu(self):
        m = tk.Menu(self)
        self.config(menu=m)
        f = tk.Menu(m, tearoff=0)
        f.add_command(label="Export Laporan ke CSV...", command=self.export_csv)
        f.add_separator()
        f.add_command(label="Keluar", command=self.destroy)
        m.add_cascade(label="File", menu=f)
        k = tk.Menu(m, tearoff=0)
        k.add_command(label="Tambah Karyawan...", command=self.emp_add)
        k.add_command(label="Refresh Semua", command=self.refresh_all)
        m.add_cascade(label="Karyawan", menu=k)
        h = tk.Menu(m, tearoff=0)
        h.add_command(label="Tentang...", command=lambda: messagebox.showinfo(
            "Tentang", f"{APP_TITLE}\nGaji mingguan + lembur + pembulatan menit.\nData tersimpan lokal (SQLite)."))
        m.add_cascade(label="Bantuan", menu=h)

    # ----- dashboard -----
    def _build_dash(self):
        ttk.Label(self.tab_dash, text="Dashboard", style="Title.TLabel").pack(anchor="w", padx=12, pady=(12, 4))
        ttk.Label(self.tab_dash, text="Ringkasan minggu berjalan. Klik Refresh untuk update.",
                  foreground="#64748B").pack(anchor="w", padx=12)
        row = ttk.Frame(self.tab_dash)
        row.pack(fill="x", padx=12, pady=12)
        self.dash_vars = {}
        for key, title in [("karyawan", "Karyawan Aktif"), ("jam", "Total Jam Minggu Ini"),
                           ("gaji", "Total Gaji Minggu Ini")]:
            card = ttk.Frame(row, style="Card.TFrame", padding=14)
            card.pack(side="left", fill="both", expand=True, padx=(0 if key == "karyawan" else 8, 0))
            ttk.Label(card, text=title, style="Card.TLabel", foreground="#64748B").pack(anchor="w")
            v = tk.StringVar(value="-")
            ttk.Label(card, textvariable=v, style="Card.TLabel",
                      font=("Segoe UI", 20, "bold"), foreground="#1E40AF").pack(anchor="w")
            self.dash_vars[key] = v
        ttk.Button(self.tab_dash, text="Refresh", command=self.refresh_all).pack(anchor="w", padx=12)
        ttk.Button(self.tab_dash, text="Ke Tab Hitung Gaji ->",
                   command=lambda: self.notebook.select(self.tab_hitung)).pack(anchor="w", padx=12, pady=6)

    # ----- karyawan -----
    def _build_emp(self):
        bar = ttk.Frame(self.tab_emp)
        bar.pack(fill="x", padx=12, pady=12)
        ttk.Label(bar, text="Data Karyawan", style="Title.TLabel").pack(side="left")
        ttk.Button(bar, text="+ Tambah", style="Primary.TButton", command=self.emp_add).pack(side="right", padx=4)
        ttk.Button(bar, text="Ubah", command=self.emp_edit).pack(side="right", padx=4)
        ttk.Button(bar, text="Hapus", command=self.emp_del).pack(side="right", padx=4)
        cols = ("id", "nama", "jabatan", "upah")
        self.emp_tree = ttk.Treeview(self.tab_emp, columns=cols, show="headings", height=15)
        for c, t, w in [("id", "ID", 50), ("nama", "Nama", 260),
                        ("jabatan", "Jabatan", 200), ("upah", "Upah/Jam", 160)]:
            self.emp_tree.heading(c, text=t)
            self.emp_tree.column(c, width=w, anchor="w" if c != "upah" else "e")
        self.emp_tree.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.emp_tree.bind("<Double-1>", lambda e: self.emp_edit())

    def _emp_rows(self):
        con = db()
        rows = con.execute("SELECT id, nama, jabatan, upah FROM employees WHERE aktif=1 ORDER BY nama").fetchall()
        con.close()
        return rows

    def refresh_emp(self):
        for i in self.emp_tree.get_children():
            self.emp_tree.delete(i)
        for r in self._emp_rows():
            self.emp_tree.insert("", "end", values=(r[0], r[1], r[2], rupiah(r[3])))

    def _emp_dialog(self, title, nama="", jabatan="", upah=""):
        d = tk.Toplevel(self)
        d.title(title)
        d.geometry("380x260")
        d.transient(self)
        d.grab_set()
        vars_ = {"nama": tk.StringVar(value=nama), "jabatan": tk.StringVar(value=jabatan),
                 "upah": tk.StringVar(value=str(upah))}
        for i, (k, lbl) in enumerate([("nama", "Nama *"), ("jabatan", "Jabatan"), ("upah", "Upah per jam (Rp) *")]):
            ttk.Label(d, text=lbl).grid(row=i, column=0, sticky="w", padx=14, pady=8)
            ttk.Entry(d, textvariable=vars_[k], width=28).grid(row=i, column=1, padx=14, pady=8)
        out = {}
        def ok():
            n = vars_["nama"].get().strip()
            try:
                u = float(vars_["upah"].get().replace(".", "").replace(",", "") or 0)
            except ValueError:
                messagebox.showerror("Error", "Upah harus angka.", parent=d)
                return
            if not n or u <= 0:
                messagebox.showerror("Error", "Nama dan upah wajib diisi.", parent=d)
                return
            out.update(nama=n, jabatan=vars_["jabatan"].get().strip(), upah=u)
            d.destroy()
        ttk.Button(d, text="Simpan", style="Primary.TButton", command=ok).grid(row=3, column=1, sticky="e", padx=14, pady=12)
        self.wait_window(d)
        return out or None

    def emp_add(self):
        r = self._emp_dialog("Tambah Karyawan")
        if not r:
            return
        con = db()
        con.execute("INSERT INTO employees(nama,jabatan,upah) VALUES(?,?,?)", (r["nama"], r["jabatan"], r["upah"]))
        con.commit()
        con.close()
        self.refresh_all()
        self.status.set(f"Karyawan '{r['nama']}' ditambahkan.")

    def _emp_selected(self):
        sel = self.emp_tree.selection()
        if not sel:
            messagebox.showinfo("Info", "Pilih karyawan dulu.")
            return None
        return self.emp_tree.item(sel[0], "values")

    def emp_edit(self):
        v = self._emp_selected()
        if not v:
            return
        eid, nama, jab, upah_txt = v
        upah_num = upah_txt.replace("Rp ", "").replace(".", "")
        r = self._emp_dialog("Ubah Karyawan", nama, jab, upah_num)
        if not r:
            return
        con = db()
        con.execute("UPDATE employees SET nama=?,jabatan=?,upah=? WHERE id=?", (r["nama"], r["jabatan"], r["upah"], eid))
        con.commit()
        con.close()
        self.refresh_all()

    def emp_del(self):
        v = self._emp_selected()
        if not v:
            return
        if not messagebox.askyesno("Hapus", f"Hapus {v[1]}? (riwayat gaji tetap tersimpan)"):
            return
        con = db()
        con.execute("UPDATE employees SET aktif=0 WHERE id=?", (v[0],))
        con.commit()
        con.close()
        self.refresh_all()

    # ----- hitung gaji -----
    def _build_hitung(self):
        ttk.Label(self.tab_hitung, text="Hitung Gaji Mingguan", style="Title.TLabel").pack(anchor="w", padx=12, pady=(12, 4))
        frm = ttk.Frame(self.tab_hitung)
        frm.pack(fill="x", padx=12, pady=8)
        ttk.Label(frm, text="Karyawan:").grid(row=0, column=0, sticky="w", pady=6)
        self.h_emp = tk.StringVar()
        self.h_emp_box = ttk.Combobox(frm, textvariable=self.h_emp, width=32, state="readonly")
        self.h_emp_box.grid(row=0, column=1, sticky="w", pady=6, padx=8)
        self.h_emp_box.bind("<<ComboboxSelected>>", lambda e: self._hitung_autofill())
        self.h_inputs = {}
        fields = [("jam_normal", "Jam normal minggu ini", "48"),
                  ("jam_lembur", "Jam lembur", "0"),
                  ("jam_libur", "Jam lembur hari libur", "0"),
                  ("menit", "Menit tambahan", "0")]
        for i, (k, lbl, dflt) in enumerate(fields, start=1):
            ttk.Label(frm, text=lbl + ":").grid(row=i, column=0, sticky="w", pady=6)
            sv = tk.StringVar(value=dflt)
            ttk.Entry(frm, textvariable=sv, width=14).grid(row=i, column=1, sticky="w", pady=6, padx=8)
            self.h_inputs[k] = sv
        btns = ttk.Frame(self.tab_hitung)
        btns.pack(fill="x", padx=12, pady=4)
        ttk.Button(btns, text="Hitung", style="Primary.TButton", command=self.do_hitung).pack(side="left", padx=(0, 8))
        ttk.Button(btns, text="Simpan ke Laporan", command=self.do_simpan).pack(side="left")
        self.h_result = tk.StringVar(value="Isi form lalu klik Hitung.")
        res = ttk.Frame(self.tab_hitung, style="Card.TFrame", padding=14)
        res.pack(fill="both", expand=True, padx=12, pady=12)
        ttk.Label(res, text="Hasil Perhitungan", style="Card.TLabel",
                  font=("Segoe UI", 12, "bold"), foreground="#1E40AF").pack(anchor="w")
        ttk.Label(res, textvariable=self.h_result, style="Card.TLabel",
                  font=("Segoe UI", 11), justify="left").pack(anchor="w", pady=8)
        self._last_hit = None

    def _h_emp_map(self):
        return {f"{r[1]} ({r[2]})" if r[2] else r[1]: r for r in self._emp_rows()}

    def refresh_hitung_combo(self):
        m = self._h_emp_map()
        self.h_emp_box["values"] = sorted(m.keys())
        if m and self.h_emp.get() not in m:
            self.h_emp.set(sorted(m.keys())[0])

    def _h_parse(self):
        m = self._h_emp_map()
        key = self.h_emp.get()
        if key not in m:
            messagebox.showinfo("Info", "Pilih karyawan dulu (tambah di tab Data Karyawan).")
            return None
        eid, nama, jab, upah = m[key]
        try:
            vals = {k: float(v.get().replace(",", ".") or 0) for k, v in self.h_inputs.items()}
        except ValueError:
            messagebox.showerror("Error", "Jam/menit harus angka.")
            return None
        if any(x < 0 for x in vals.values()):
            messagebox.showerror("Error", "Tidak boleh negatif.")
            return None
        return eid, nama, upah, int(vals["menit"]), vals

    def do_hitung(self):
        p = self._h_parse()
        if not p:
            return
        eid, nama, upah, menit, vals = p
        r = hitung_gaji(upah, vals["jam_normal"], vals["jam_lembur"], vals["jam_libur"], menit, self.settings)
        self._last_hit = (eid, nama, vals, menit, r)
        self.h_result.set(
            f"Karyawan : {nama}  (upah {rupiah(upah)}/jam)\n"
            f"Gaji pokok        : {rupiah(r['pokok'])}\n"
            f"Gaji lembur       : {rupiah(r['lembur'])}  ({r['jam_lembur_total']:.2f} jam)\n"
            f"Gaji lembur libur : {rupiah(r['libur'])}\n"
            f"TOTAL MINGGUAN    : {rupiah(r['total'])}")
        self.status.set(f"Perhitungan {nama}: {rupiah(r['total'])}")

    def do_simpan(self):
        if not self._last_hit:
            messagebox.showinfo("Info", "Klik Hitung dulu.")
            return
        eid, nama, vals, menit, r = self._last_hit
        con = db()
        con.execute("""INSERT INTO records(employee_id,tanggal,jam_normal,jam_lembur,jam_libur,menit,total)
                       VALUES(?,?,?,?,?,?,?)""",
                    (eid, date.today().isoformat(), vals["jam_normal"], vals["jam_lembur"],
                     vals["jam_libur"], menit, r["total"]))
        con.commit()
        con.close()
        self.refresh_all()
        self.status.set(f"Gaji {nama} ({rupiah(r['total'])}) tersimpan.")
        messagebox.showinfo("Tersimpan", f"Gaji {nama} sebesar {rupiah(r['total'])} tersimpan ke Laporan.")

    # ----- laporan -----
    def _build_lap(self):
        bar = ttk.Frame(self.tab_lap)
        bar.pack(fill="x", padx=12, pady=12)
        ttk.Label(bar, text="Laporan Gaji", style="Title.TLabel").pack(side="left")
        ttk.Button(bar, text="Export CSV...", command=self.export_csv).pack(side="right", padx=4)
        ttk.Button(bar, text="Hapus Baris", command=self.lap_del).pack(side="right", padx=4)
        cols = ("id", "tanggal", "nama", "normal", "lembur", "libur", "menit", "total")
        self.lap_tree = ttk.Treeview(self.tab_lap, columns=cols, show="headings", height=14)
        hdr = [("id", "ID", 45), ("tanggal", "Tanggal", 110), ("nama", "Nama", 200),
               ("normal", "Normal", 80), ("lembur", "Lembur", 80), ("libur", "Libur", 80),
               ("menit", "Menit", 70), ("total", "Total", 150)]
        for c, t, w in hdr:
            self.lap_tree.heading(c, text=t)
            self.lap_tree.column(c, width=w, anchor="e" if c in ("normal", "lembur", "libur", "menit", "total") else "w")
        self.lap_tree.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    def refresh_lap(self):
        for i in self.lap_tree.get_children():
            self.lap_tree.delete(i)
        con = db()
        rows = con.execute("""SELECT r.id, r.tanggal, e.nama, r.jam_normal, r.jam_lembur,
                              r.jam_libur, r.menit, r.total FROM records r
                              LEFT JOIN employees e ON e.id=r.employee_id
                              ORDER BY r.id DESC LIMIT 500""").fetchall()
        con.close()
        for r in rows:
            self.lap_tree.insert("", "end", values=(r[0], r[1], r[2], r[3], r[4], r[5], r[6], rupiah(r[7])))

    def lap_del(self):
        sel = self.lap_tree.selection()
        if not sel:
            messagebox.showinfo("Info", "Pilih baris dulu.")
            return
        v = self.lap_tree.item(sel[0], "values")
        if not messagebox.askyesno("Hapus", f"Hapus record #{v[0]} ({v[2]}, {v[7]})?"):
            return
        con = db()
        con.execute("DELETE FROM records WHERE id=?", (v[0],))
        con.commit()
        con.close()
        self.refresh_all()

    def export_csv(self):
        con = db()
        rows = con.execute("""SELECT r.id, r.tanggal, e.nama, e.jabatan, r.jam_normal, r.jam_lembur,
                              r.jam_libur, r.menit, r.total FROM records r
                              LEFT JOIN employees e ON e.id=r.employee_id ORDER BY r.id DESC""").fetchall()
        con.close()
        if not rows:
            messagebox.showinfo("Info", "Belum ada data.")
            return
        p = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")],
                                         initialfile="laporan_gaji.csv")
        if not p:
            return
        with open(p, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["ID", "Tanggal", "Nama", "Jabatan", "Jam Normal", "Jam Lembur",
                        "Jam Libur", "Menit", "Total (Rp)"])
            w.writerows(rows)
        self.status.set(f"Export {len(rows)} baris ke {p}")
        messagebox.showinfo("Selesai", f"{len(rows)} baris tersimpan ke:\n{p}")

    # ----- pengaturan -----
    def _build_set(self):
        ttk.Label(self.tab_set, text="Pengaturan Perhitungan", style="Title.TLabel").pack(anchor="w", padx=12, pady=(12, 4))
        frm = ttk.Frame(self.tab_set)
        frm.pack(fill="x", padx=12, pady=8)
        self.s_vars = {}
        fields = [("upah_per_jam", "Upah default per jam (Rp)"), ("jam_per_hari", "Jam kerja normal / hari"),
                  ("hari_per_minggu", "Hari kerja / minggu"), ("rate_lembur", "Rate lembur (x)"),
                  ("rate_libur", "Rate lembur hari libur (x)"), ("pembulatan_menit", "Pembulatan menit ke atas")]
        for i, (k, lbl) in enumerate(fields):
            ttk.Label(frm, text=lbl + ":").grid(row=i, column=0, sticky="w", pady=6)
            sv = tk.StringVar(value=str(self.settings[k]))
            ttk.Entry(frm, textvariable=sv, width=16).grid(row=i, column=1, sticky="w", pady=6, padx=8)
            self.s_vars[k] = sv
        ttk.Button(frm, text="Simpan Pengaturan", style="Primary.TButton",
                   command=self.save_set).grid(row=len(fields), column=1, sticky="w", pady=12)

    def save_set(self):
        try:
            ns = {}
            for k, sv in self.s_vars.items():
                v = float(sv.get().replace(",", "."))
                ns[k] = int(v) if k in ("hari_per_minggu", "pembulatan_menit") else v
            assert ns["upah_per_jam"] > 0 and ns["jam_per_hari"] > 0 and ns["hari_per_minggu"] > 0
            assert ns["rate_lembur"] > 0 and ns["rate_libur"] > 0 and ns["pembulatan_menit"] > 0
        except (ValueError, AssertionError):
            messagebox.showerror("Error", "Semua nilai harus angka positif.")
            return
        self.settings = ns
        save_settings(ns)
        self.status.set("Pengaturan tersimpan.")
        messagebox.showinfo("Tersimpan", "Pengaturan berhasil disimpan.")

    def refresh_set(self):
        for k, sv in self.s_vars.items():
            sv.set(str(self.settings[k]))

    # ----- global -----
    def refresh_all(self):
        self.settings = load_settings()
        self.refresh_emp()
        self.refresh_hitung_combo()
        self.refresh_lap()
        if hasattr(self, "s_vars"):
            self.refresh_set()
        con = db()
        nk = con.execute("SELECT COUNT(*) FROM employees WHERE aktif=1").fetchone()[0]
        week = date.today().isocalendar()[1]
        rows = con.execute("SELECT jam_normal,jam_lembur,jam_libur,total,tanggal FROM records").fetchall()
        con.close()
        tj = sum((r[0] + r[1] + r[2]) for r in rows
                 if len(r[4]) >= 10 and date.fromisoformat(r[4]).isocalendar()[1] == week)
        tg = sum(r[3] for r in rows
                 if len(r[4]) >= 10 and date.fromisoformat(r[4]).isocalendar()[1] == week)
        self.dash_vars["karyawan"].set(str(nk))
        self.dash_vars["jam"].set(f"{tj:.1f} jam")
        self.dash_vars["gaji"].set(rupiah(tg))


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
