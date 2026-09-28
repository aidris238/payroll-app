#!/usr/bin/env python3
"""PayrollPro v3 - Aplikasi Penggajian Karyawan Mingguan (GUI Desktop).
Stdlib only: tkinter + sqlite3 + csv + json. Lihat docs/PRD-v3.md.
Jalankan: python payroll_gui.py  (atau run.bat / run.sh)
"""

import csv
import json
import os
import sqlite3
import sys
import tkinter as tk
from datetime import date
from tkinter import filedialog, ttk

APP_TITLE = "PayrollPro - Penggajian Karyawan Mingguan"
APP_VERSION = "v3.0"


def app_dir() -> str:
    # Saat frozen PyInstaller, data harus di folder EXE, bukan _MEI temp.
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


DB_FILE = os.path.join(app_dir(), "payroll.db")
SETTINGS_FILE = os.path.join(app_dir(), "settings.json")

DEFAULT_SETTINGS = {
    "upah_per_jam": 50000,
    "jam_per_hari": 8.0,
    "hari_per_minggu": 6,
    "rate_lembur": 1.5,
    "rate_libur": 2.0,
    "pembulatan_menit": 15,
}

# ---------------- logika murni (tanpa GUI, bisa di-test) ----------------

def bulatkan_menit(menit: int, pembulatan: int = 15) -> float:
    if menit <= 0:
        return 0.0
    return ((menit + pembulatan - 1) // pembulatan) * (pembulatan / 60)


def hitung_gaji(upah, jam_normal, jam_lembur, jam_libur, menit, s):
    jam_std = s["jam_per_hari"] * s["hari_per_minggu"]
    normal_dibayar = min(jam_normal, jam_std)
    lebih = max(0.0, jam_normal - jam_std)
    menit_jam = bulatkan_menit(int(menit), s["pembulatan_menit"])
    total_lembur = lebih + jam_lembur + menit_jam
    pokok = normal_dibayar * upah
    lembur = total_lembur * upah * s["rate_lembur"]
    libur = jam_libur * upah * s["rate_libur"]
    return {
        "pokok": pokok, "lembur": lembur, "libur": libur,
        "total": pokok + lembur + libur,
        "jam_std": jam_std, "normal_dibayar": normal_dibayar,
        "lebih": lebih, "menit_jam": menit_jam,
        "jam_lembur_total": total_lembur,
    }


def rupiah(x) -> str:
    try:
        return f"Rp {float(x):,.0f}".replace(",", ".")
    except (ValueError, TypeError):
        return "Rp 0"


def parse_angka(txt: str):
    """Terima '50.000', '50000', '8,5', '8.5' -> float. Return None bila invalid."""
    if txt is None:
        return None
    t = txt.strip().replace("Rp", "").replace(" ", "")
    if not t:
        return None
    if "," in t and "." in t:
        t = t.replace(".", "").replace(",", ".")  # 1.234,5 -> 1234.5
    elif "," in t:
        t = t.replace(",", ".")  # 8,5 -> 8.5
    elif t.count(".") > 1:
        t = t.replace(".", "")  # 50.000.000 -> 50000000
    elif t.count(".") == 1:
        # Satu titik ambigu: "50.000" (ribuan, ID) vs "8.5" (desimal).
        # Konvensi ID: titik ribuan selalu diikuti tepat 3 digit.
        int_part, frac_part = t.split(".")
        if len(frac_part) == 3 and int_part and int_part.lstrip("-").isdigit():
            t = int_part + frac_part  # 50.000 -> 50000
        # selain itu biarkan sebagai desimal: 8.5 -> 8.5
    try:
        return float(t)
    except ValueError:
        return None


def fmt_ribu(x) -> str:
    try:
        return f"{float(x):,.0f}".replace(",", ".")
    except (ValueError, TypeError):
        return "0"


# ---------------- settings & db ----------------

def load_settings():
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            d = json.load(f)
        out = dict(DEFAULT_SETTINGS)
        for k in out:
            if k in d:
                try:
                    out[k] = int(d[k]) if k in ("hari_per_minggu", "pembulatan_menit") else float(d[k])
                except (ValueError, TypeError):
                    pass
        return out
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(DEFAULT_SETTINGS)


def save_settings(s):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
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
    con.commit()
    return con


# ---------------- popup custom ----------------

class Popup(tk.Toplevel):
    """Base popup modal: centered ke parent, ada judul + icon teks + tombol."""

    ICONS = {"info": ("\u2139", "#2563EB"), "ok": ("\u2714", "#16A34A"),
             "warn": ("\u26a0", "#D97706"), "error": ("\u2716", "#DC2626")}

    def __init__(self, parent, title, message, kind="info", buttons=("OK",), width=420):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.transient(parent)
        self.result = None
        glyph, color = self.ICONS.get(kind, self.ICONS["info"])

        head = ttk.Frame(self, padding=(18, 14, 18, 4))
        head.pack(fill="x")
        tk.Label(head, text=glyph, font=("Segoe UI", 22, "bold"), fg=color).pack(side="left", padx=(0, 12))
        tk.Label(head, text=title, font=("Segoe UI", 12, "bold")).pack(side="left", anchor="w")

        msg = tk.Label(self, text=message, font=("Segoe UI", 10), justify="left",
                       wraplength=width - 40, anchor="w")
        msg.pack(fill="x", padx=18, pady=(4, 8))

        bar = ttk.Frame(self, padding=(18, 4, 18, 14))
        bar.pack(fill="x")
        for i, b in enumerate(buttons):
            ttk.Button(bar, text=b, style="Primary.TButton" if i == 0 else "TButton",
                       command=lambda v=b: self._close(v)).pack(side="right", padx=(8, 0))
        self.bind("<Return>", lambda e: self._close(buttons[0]))
        self.bind("<Escape>", lambda e: self._close(None))
        self.protocol("WM_DELETE_WINDOW", lambda: self._close(None))
        self.update_idletasks()
        self._center(parent, width)
        self.grab_set()
        self.wait_window(self)

    def _center(self, parent, width):
        try:
            px, py = parent.winfo_rootx(), parent.winfo_rooty()
            pw, ph = parent.winfo_width(), parent.winfo_height()
            h = self.winfo_reqheight()
            x = px + max(0, (pw - width) // 2)
            y = py + max(0, (ph - h) // 2)
        except tk.TclError:
            x = y = 100
            h = self.winfo_reqheight()
        self.geometry(f"{width}x{h}+{x}+{y}")

    def _close(self, v):
        self.result = v
        self.grab_release()
        self.destroy()


def popup_info(parent, title, msg):
    Popup(parent, title, msg, "info")


def popup_ok(parent, title, msg):
    Popup(parent, title, msg, "ok")


def popup_error(parent, title, msg):
    Popup(parent, title, msg, "error")


def popup_confirm(parent, title, msg, ok_label="Ya", cancel="Batal") -> bool:
    return Popup(parent, title, msg, "warn", (ok_label, cancel)).result == ok_label


class SlipPopup(tk.Toplevel):
    """Popup slip gaji: teks monospace rapi + tombol aksi."""

    def __init__(self, parent, slip_text, total_str, on_save_report, on_save_txt):
        super().__init__(parent)
        self.title("Slip Gaji Mingguan")
        self.resizable(True, True)
        self.transient(parent)
        head = ttk.Frame(self, padding=(16, 12, 16, 4))
        head.pack(fill="x")
        tk.Label(head, text="\U0001f9fe", font=("Segoe UI", 20)).pack(side="left", padx=(0, 10))
        tk.Label(head, text="Slip Gaji Mingguan", font=("Segoe UI", 12, "bold")).pack(side="left")
        tk.Label(head, text=total_str, font=("Segoe UI", 12, "bold"), fg="#1E40AF").pack(side="right")
        txt = tk.Text(self, font=("Consolas", 10), width=52, height=18,
                      relief="solid", borderwidth=1, padx=10, pady=10)
        txt.insert("1.0", slip_text)
        txt.config(state="disabled")
        txt.pack(fill="both", expand=True, padx=16, pady=8)
        bar = ttk.Frame(self, padding=(16, 4, 16, 14))
        bar.pack(fill="x")
        ttk.Button(bar, text="Salin Total", command=lambda: self._copy(total_str)).pack(side="left")
        ttk.Button(bar, text="Simpan .txt", command=on_save_txt).pack(side="left", padx=8)
        ttk.Button(bar, text="Tutup", command=self._close).pack(side="right")
        ttk.Button(bar, text="Simpan ke Laporan", style="Primary.TButton",
                   command=lambda: (on_save_report(), self._close())).pack(side="right", padx=8)
        self.bind("<Escape>", lambda e: self._close())
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.update_idletasks()
        try:
            px, py = parent.winfo_rootx(), parent.winfo_rooty()
            self.geometry(f"+{px + 60}+{py + 40}")
        except tk.TclError:
            pass
        self.grab_set()
        self.wait_window(self)

    def _copy(self, s):
        self.clipboard_clear()
        self.clipboard_append(s)

    def _close(self):
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()


def slip_text(nama, upah, vals, menit, r, tanggal) -> str:
    L = 40
    g = [f"SLIP GAJI MINGGUAN", f"Tanggal: {tanggal}", "-" * L,
         f"Karyawan : {nama}", f"Upah/jam : {rupiah(upah)}", "-" * L,
         f"Gaji pokok        : {rupiah(r['pokok']):>14}",
         f"  ({r['normal_dibayar']:.1f} jam normal)",
         f"Gaji lembur       : {rupiah(r['lembur']):>14}",
         f"  ({r['jam_lembur_total']:.2f} jam x {rupiah(upah)}/jam)",
         f"Gaji lembur libur : {rupiah(r['libur']):>14}",
         f"  ({vals['jam_libur']:.1f} jam libur)", "-" * L,
         f"TOTAL             : {rupiah(r['total']):>14}", "-" * L,
         f"Rincian: normal {vals['jam_normal']:.1f}j, lembur {vals['jam_lembur']:.1f}j,",
         f"libur {vals['jam_libur']:.1f}j, menit {menit} -> {r['menit_jam']:.2f}j"]
    return "\n".join(g)


# ---------------- aplikasi ----------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_TITLE} {APP_VERSION}")
        self.geometry("1000x660")
        self.minsize(900, 580)
        self.settings = load_settings()
        self._style()
        self._menu()
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        self.tabs = {}
        for key, label in [("dash", "  \U0001f3e0 Dashboard  "),
                           ("emp", "  \U0001f464 Data Karyawan  "),
                           ("hitung", "  \U0001f9ee Hitung Gaji  "),
                           ("lap", "  \U0001f4ca Laporan  "),
                           ("set", "  \u2699\ufe0f Pengaturan  ")]:
            f = ttk.Frame(self.notebook)
            self.notebook.add(f, text=label)
            self.tabs[key] = f
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
        st.configure("Card.TFrame", background="white", relief="solid", borderwidth=1)
        st.configure("Card.TLabel", background="white")
        st.configure("TButton", font=("Segoe UI", 10), padding=6)
        st.configure("Primary.TButton", background=P, foreground="white")
        st.map("Primary.TButton", background=[("active", DARK)])
        st.configure("Treeview", font=("Segoe UI", 10), rowheight=26)
        st.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        st.configure("Status.TLabel", font=("Segoe UI", 9), foreground="#475569")
        st.configure("Error.TLabel", background=BG, font=("Segoe UI", 9), foreground="#DC2626")

    def _menu(self):
        m = tk.Menu(self)
        self.config(menu=m)
        f = tk.Menu(m, tearoff=0)
        f.add_command(label="Export Laporan ke CSV...", command=self.export_csv)
        f.add_command(label="Backup Database...", command=self.backup_db)
        f.add_separator()
        f.add_command(label="Keluar", command=self.destroy)
        m.add_cascade(label="File", menu=f)
        k = tk.Menu(m, tearoff=0)
        k.add_command(label="Tambah Karyawan...", command=self.emp_add)
        k.add_command(label="Refresh Semua", command=self.refresh_all)
        m.add_cascade(label="Karyawan", menu=k)
        h = tk.Menu(m, tearoff=0)
        h.add_command(label="Cara Pakai...", command=self.help_dialog)
        h.add_command(label="Tentang...", command=lambda: popup_info(
            self, "Tentang", f"{APP_TITLE} {APP_VERSION}\nGaji mingguan + lembur + pembulatan menit.\nData tersimpan lokal (SQLite)."))
        m.add_cascade(label="Bantuan", menu=h)

    def help_dialog(self):
        popup_info(self, "Cara Pakai",
                   "1. Tab Data Karyawan: tambah nama + upah/jam.\n"
                   "2. Tab Hitung Gaji: pilih karyawan, isi jam & menit.\n"
                   "   Hasil terhitung otomatis, klik Slip / Simpan.\n"
                   "3. Tab Laporan: cari, filter, export CSV.\n"
                   "4. Tab Pengaturan: ubah rate & jam standar.")

    # ----- dashboard -----
    def _build_dash(self):
        t = self.tabs["dash"]
        ttk.Label(t, text="Dashboard", style="Title.TLabel").pack(anchor="w", padx=12, pady=(12, 4))
        ttk.Label(t, text="Ringkasan minggu berjalan.",
                  foreground="#64748B").pack(anchor="w", padx=12)
        row = ttk.Frame(t)
        row.pack(fill="x", padx=12, pady=12)
        self.dash_vars = {}
        for key, title in [("karyawan", "Karyawan Aktif"), ("jam", "Total Jam Minggu Ini"),
                           ("gaji", "Total Gaji Minggu Ini")]:
            card = ttk.Frame(row, style="Card.TFrame", padding=14)
            card.pack(side="left", fill="both", expand=True, padx=(0 if key == "karyawan" else 8, 0))
            ttk.Label(card, text=title, style="Card.TLabel", foreground="#64748B").pack(anchor="w")
            v = tk.StringVar(value="-")
            tk.Label(card, textvariable=v, bg="white",
                     font=("Segoe UI", 20, "bold"), fg="#1E40AF").pack(anchor="w")
            self.dash_vars[key] = v
        btns = ttk.Frame(t)
        btns.pack(fill="x", padx=12)
        ttk.Button(btns, text="Refresh", command=self.refresh_all).pack(side="left")
        ttk.Button(btns, text="Hitung Gaji \u2192", style="Primary.TButton",
                   command=lambda: self.notebook.select(self.tabs["hitung"])).pack(side="left", padx=8)
        ttk.Label(t, text="5 Transaksi Terakhir:", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=12, pady=(12, 4))
        cols = ("tanggal", "nama", "total")
        self.dash_tree = ttk.Treeview(t, columns=cols, show="headings", height=6)
        for c, tt, w in [("tanggal", "Tanggal", 130), ("nama", "Nama", 300), ("total", "Total", 180)]:
            self.dash_tree.heading(c, text=tt)
            self.dash_tree.column(c, width=w, anchor="e" if c == "total" else "w")
        self.dash_tree.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    # ----- karyawan -----
    def _build_emp(self):
        t = self.tabs["emp"]
        bar = ttk.Frame(t)
        bar.pack(fill="x", padx=12, pady=12)
        ttk.Label(bar, text="Data Karyawan", style="Title.TLabel").pack(side="left")
        ttk.Button(bar, text="Hapus", command=self.emp_del).pack(side="right", padx=4)
        ttk.Button(bar, text="Ubah", command=self.emp_edit).pack(side="right", padx=4)
        ttk.Button(bar, text="+ Tambah", style="Primary.TButton", command=self.emp_add).pack(side="right", padx=4)
        cols = ("id", "nama", "jabatan", "upah")
        self.emp_tree = ttk.Treeview(t, columns=cols, show="headings", height=15)
        for c, tt, w in [("id", "ID", 50), ("nama", "Nama", 260),
                         ("jabatan", "Jabatan", 200), ("upah", "Upah/Jam", 160)]:
            self.emp_tree.heading(c, text=tt)
            self.emp_tree.column(c, width=w, anchor="e" if c == "upah" else "w")
        self.emp_tree.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.emp_tree.bind("<Double-1>", lambda e: self.emp_edit())

    def _emp_rows(self):
        con = db()
        try:
            return con.execute(
                "SELECT id, nama, jabatan, upah FROM employees WHERE aktif=1 ORDER BY nama").fetchall()
        finally:
            con.close()

    def refresh_emp(self):
        for i in self.emp_tree.get_children():
            self.emp_tree.delete(i)
        for r in self._emp_rows():
            self.emp_tree.insert("", "end", values=(r[0], r[1], r[2], rupiah(r[3])))

    def _emp_dialog(self, title, nama="", jabatan="", upah=""):
        d = tk.Toplevel(self)
        d.title(title)
        d.geometry("400x300")
        d.transient(self)
        vars_ = {"nama": tk.StringVar(value=nama), "jabatan": tk.StringVar(value=jabatan),
                 "upah": tk.StringVar(value=str(upah))}
        errs = {}
        for i, (k, lbl) in enumerate([("nama", "Nama *"), ("jabatan", "Jabatan"), ("upah", "Upah per jam (Rp) *")]):
            ttk.Label(d, text=lbl).grid(row=i * 2, column=0, columnspan=2, sticky="w", padx=14, pady=(10, 0))
            ttk.Entry(d, textvariable=vars_[k], width=32).grid(row=i * 2 + 1, column=0, columnspan=2,
                                                              sticky="we", padx=14)
            e = ttk.Label(d, text="", style="Error.TLabel")
            e.grid(row=i * 2 + 1, column=2, sticky="w") if False else None
            errs[k] = e

        def validate():
            ok = True
            if not vars_["nama"].get().strip():
                popup_error(d, "Belum Lengkap", "Nama karyawan wajib diisi.")
                return False
            u = parse_angka(vars_["upah"].get())
            if u is None or u <= 0:
                popup_error(d, "Upah Salah", "Upah per jam harus angka lebih dari 0.\nContoh: 50000")
                return False
            return ok

        out = {}

        def ok():
            if not validate():
                return
            out.update(nama=vars_["nama"].get().strip(),
                       jabatan=vars_["jabatan"].get().strip(),
                       upah=parse_angka(vars_["upah"].get()))
            d.destroy()

        btns = ttk.Frame(d)
        btns.grid(row=7, column=0, columnspan=2, sticky="e", padx=14, pady=16)
        ttk.Button(btns, text="Batal", command=d.destroy).pack(side="right")
        ttk.Button(btns, text="Simpan", style="Primary.TButton", command=ok).pack(side="right", padx=8)
        d.bind("<Return>", lambda e: ok())
        d.protocol("WM_DELETE_WINDOW", d.destroy)
        d.update_idletasks()
        try:
            x = self.winfo_rootx() + (self.winfo_width() - 400) // 2
            y = self.winfo_rooty() + (self.winfo_height() - 300) // 2
            d.geometry(f"+{x}+{y}")
        except tk.TclError:
            pass
        d.grab_set()
        self.wait_window(d)
        return out or None

    def emp_add(self):
        r = self._emp_dialog("Tambah Karyawan")
        if not r:
            return
        con = db()
        try:
            con.execute("INSERT INTO employees(nama,jabatan,upah) VALUES(?,?,?)",
                        (r["nama"], r["jabatan"], r["upah"]))
            con.commit()
        finally:
            con.close()
        self.refresh_all()
        self.status.set(f"Karyawan '{r['nama']}' ditambahkan.")
        popup_ok(self, "Berhasil", f"Karyawan '{r['nama']}' ditambahkan.")

    def _emp_selected(self):
        sel = self.emp_tree.selection()
        if not sel:
            popup_info(self, "Pilih Dulu", "Klik salah satu baris karyawan dulu.")
            return None
        return self.emp_tree.item(sel[0], "values")

    def emp_edit(self):
        v = self._emp_selected()
        if not v:
            return
        eid, nama, jab, upah_txt = v
        r = self._emp_dialog("Ubah Karyawan", nama, jab,
                             upah_txt.replace("Rp ", "").replace(".", ""))
        if not r:
            return
        con = db()
        try:
            con.execute("UPDATE employees SET nama=?,jabatan=?,upah=? WHERE id=?",
                        (r["nama"], r["jabatan"], r["upah"], eid))
            con.commit()
        finally:
            con.close()
        self.refresh_all()
        popup_ok(self, "Berhasil", "Data karyawan diperbarui.")

    def emp_del(self):
        v = self._emp_selected()
        if not v:
            return
        if not popup_confirm(self, "Hapus Karyawan",
                             f"Hapus {v[1]}?\nRiwayat gaji yang sudah tersimpan tidak ikut terhapus."):
            return
        con = db()
        try:
            con.execute("UPDATE employees SET aktif=0 WHERE id=?", (v[0],))
            con.commit()
        finally:
            con.close()
        self.refresh_all()

    # ----- hitung gaji (live) -----
    def _build_hitung(self):
        t = self.tabs["hitung"]
        ttk.Label(t, text="Hitung Gaji Mingguan", style="Title.TLabel").pack(anchor="w", padx=12, pady=(12, 4))
        ttk.Label(t, text="Hasil terhitung otomatis setiap ada perubahan.",
                  foreground="#64748B").pack(anchor="w", padx=12)
        frm = ttk.Frame(t)
        frm.pack(fill="x", padx=12, pady=8)
        ttk.Label(frm, text="Karyawan:").grid(row=0, column=0, sticky="w", pady=6)
        self.h_emp = tk.StringVar()
        self.h_emp_box = ttk.Combobox(frm, textvariable=self.h_emp, width=34, state="readonly")
        self.h_emp_box.grid(row=0, column=1, sticky="w", pady=6, padx=8)
        self.h_emp_box.bind("<<ComboboxSelected>>", lambda e: self._live())
        self.h_inputs, self.h_errs = {}, {}
        fields = [("jam_normal", "Jam normal minggu ini", "48"),
                  ("jam_lembur", "Jam lembur", "0"),
                  ("jam_libur", "Jam lembur hari libur", "0"),
                  ("menit", "Menit tambahan", "0")]
        for i, (k, lbl, dflt) in enumerate(fields, start=1):
            ttk.Label(frm, text=lbl + ":").grid(row=i, column=0, sticky="w", pady=5)
            sv = tk.StringVar(value=dflt)
            sv.trace_add("write", lambda *a: self._live())
            ent = ttk.Entry(frm, textvariable=sv, width=14)
            ent.grid(row=i, column=1, sticky="w", pady=5, padx=8)
            err = ttk.Label(frm, text="", style="Error.TLabel")
            err.grid(row=i, column=2, sticky="w")
            self.h_inputs[k] = (sv, ent)
            self.h_errs[k] = err
        self.h_form_err = ttk.Label(t, text="", style="Error.TLabel")
        self.h_form_err.pack(anchor="w", padx=12)
        btns = ttk.Frame(t)
        btns.pack(fill="x", padx=12, pady=4)
        self.btn_slip = ttk.Button(btns, text="\U0001f9fe Tampilkan Slip", style="Primary.TButton",
                                   command=self.show_slip)
        self.btn_slip.pack(side="left", padx=(0, 8))
        self.btn_simpan = ttk.Button(btns, text="Simpan ke Laporan", command=self.do_simpan)
        self.btn_simpan.pack(side="left")
        res = ttk.Frame(t, style="Card.TFrame", padding=14)
        res.pack(fill="both", expand=True, padx=12, pady=12)
        tk.Label(res, text="Hasil Perhitungan (live)", bg="white",
                 font=("Segoe UI", 12, "bold"), fg="#1E40AF").pack(anchor="w")
        self.h_result = tk.StringVar(value="Pilih karyawan dan isi jam kerja.")
        tk.Label(res, textvariable=self.h_result, bg="white",
                 font=("Consolas", 11), justify="left").pack(anchor="w", pady=8)
        self._last = None

    def _h_emp_map(self):
        return {f"{r[1]} ({r[2]})" if r[2] else r[1]: r for r in self._emp_rows()}

    def refresh_hitung_combo(self):
        m = self._h_emp_map()
        cur = self.h_emp.get()
        self.h_emp_box["values"] = sorted(m.keys())
        if m and cur not in m:
            self.h_emp.set(sorted(m.keys())[0])
        self._live()

    def _live(self):
        """Hitung ulang tiap ada perubahan; validasi inline. Tidak pernah popup."""
        for e in self.h_errs.values():
            e.config(text="")
        for _, (_, ent) in self.h_inputs.items():
            try:
                ent.config(style="TEntry")
            except tk.TclError:
                pass
        self.btn_slip.config(state="disabled")
        self.btn_simpan.config(state="disabled")
        self._last = None
        m = self._h_emp_map()
        key = self.h_emp.get()
        if key not in m:
            self.h_result.set("Belum ada karyawan.\nTambahkan dulu di tab Data Karyawan.")
            return
        vals, bad = {}, False
        for k, (sv, ent) in self.h_inputs.items():
            v = parse_angka(sv.get())
            if v is None or v < 0:
                self.h_errs[k].config(text="angka \u2265 0")
                bad = True
            else:
                vals[k] = v
        if bad:
            self.h_form_err.config(text="Perbaiki field bertanda merah.")
            self.h_result.set("...")
            return
        self.h_form_err.config(text="")
        eid, nama, jab, upah = m[key]
        menit = int(vals["menit"])
        r = hitung_gaji(upah, vals["jam_normal"], vals["jam_lembur"], vals["jam_libur"], menit, self.settings)
        self._last = (eid, nama, upah, vals, menit, r)
        self.h_result.set(
            f"{nama}  ({rupiah(upah)}/jam)\n"
            f"Gaji pokok        : {rupiah(r['pokok'])}\n"
            f"Gaji lembur       : {rupiah(r['lembur'])}  ({r['jam_lembur_total']:.2f} jam)\n"
            f"Gaji lembur libur : {rupiah(r['libur'])}\n"
            f"TOTAL MINGGUAN    : {rupiah(r['total'])}")
        self.btn_slip.config(state="normal")
        self.btn_simpan.config(state="normal")

    def show_slip(self):
        if not self._last:
            popup_info(self, "Belum Siap", "Lengkapi form dulu sampai hasil muncul.")
            return
        eid, nama, upah, vals, menit, r = self._last
        tgl = date.today().isoformat()
        SlipPopup(self, slip_text(nama, upah, vals, menit, r, tgl), rupiah(r["total"]),
                  on_save_report=self.do_simpan,
                  on_save_txt=lambda: self.save_slip_txt(nama, upah, vals, menit, r, tgl))

    def save_slip_txt(self, nama, upah, vals, menit, r, tgl):
        p = filedialog.asksaveasfilename(defaultextension=".txt",
                                         filetypes=[("Text", "*.txt")],
                                         initialfile=f"slip_{nama}_{tgl}.txt".replace(" ", "_"))
        if not p:
            return
        with open(p, "w", encoding="utf-8") as f:
            f.write(slip_text(nama, upah, vals, menit, r, tgl) + "\n")
        popup_ok(self, "Tersimpan", f"Slip tersimpan ke:\n{p}")

    def do_simpan(self):
        if not self._last:
            popup_info(self, "Belum Siap", "Lengkapi form dulu sampai hasil muncul.")
            return
        eid, nama, upah, vals, menit, r = self._last
        con = db()
        try:
            con.execute("""INSERT INTO records(employee_id,tanggal,jam_normal,jam_lembur,jam_libur,menit,total)
                           VALUES(?,?,?,?,?,?,?)""",
                        (eid, date.today().isoformat(), vals["jam_normal"], vals["jam_lembur"],
                         vals["jam_libur"], menit, r["total"]))
            con.commit()
        finally:
            con.close()
        self.refresh_all()
        self.status.set(f"Gaji {nama} ({rupiah(r['total'])}) tersimpan.")
        popup_ok(self, "Tersimpan",
                 f"Gaji {nama} sebesar {rupiah(r['total'])}\ntersimpan ke tab Laporan.")

    # ----- laporan -----
    def _build_lap(self):
        t = self.tabs["lap"]
        bar = ttk.Frame(t)
        bar.pack(fill="x", padx=12, pady=12)
        ttk.Label(bar, text="Laporan Gaji", style="Title.TLabel").pack(side="left")
        ttk.Button(bar, text="Export CSV...", command=self.export_csv).pack(side="right", padx=4)
        ttk.Button(bar, text="Hapus Baris", command=self.lap_del).pack(side="right", padx=4)
        flt = ttk.Frame(t)
        flt.pack(fill="x", padx=12, pady=(0, 8))
        ttk.Label(flt, text="Cari nama:").pack(side="left")
        self.lap_q = tk.StringVar()
        self.lap_q.trace_add("write", lambda *a: self.refresh_lap())
        ttk.Entry(flt, textvariable=self.lap_q, width=24).pack(side="left", padx=8)
        self.lap_week = tk.BooleanVar(value=False)
        ttk.Checkbutton(flt, text="Minggu ini saja",
                        variable=self.lap_week, command=self.refresh_lap).pack(side="left", padx=8)
        cols = ("id", "tanggal", "nama", "normal", "lembur", "libur", "menit", "total")
        self.lap_tree = ttk.Treeview(t, columns=cols, show="headings", height=13)
        for c, tt, w in [("id", "ID", 45), ("tanggal", "Tanggal", 110), ("nama", "Nama", 200),
                         ("normal", "Normal", 75), ("lembur", "Lembur", 75), ("libur", "Libur", 75),
                         ("menit", "Menit", 65), ("total", "Total", 150)]:
            self.lap_tree.heading(c, text=tt)
            self.lap_tree.column(c, width=w,
                                 anchor="e" if c in ("normal", "lembur", "libur", "menit", "total") else "w")
        self.lap_tree.pack(fill="both", expand=True, padx=12)
        self.lap_total = tk.StringVar(value="Total: Rp 0")
        ttk.Label(t, textvariable=self.lap_total, font=("Segoe UI", 11, "bold")).pack(anchor="e", padx=12, pady=8)

    def refresh_lap(self):
        for i in self.lap_tree.get_children():
            self.lap_tree.delete(i)
        con = db()
        try:
            rows = con.execute("""SELECT r.id, r.tanggal, e.nama, r.jam_normal, r.jam_lembur,
                                  r.jam_libur, r.menit, r.total FROM records r
                                  LEFT JOIN employees e ON e.id=r.employee_id
                                  ORDER BY r.id DESC LIMIT 1000""").fetchall()
        finally:
            con.close()
        q = self.lap_q.get().strip().lower()
        cur_week = date.today().isocalendar()[1]
        tot, n = 0.0, 0
        for r in rows:
            if q and q not in (r[2] or "").lower():
                continue
            if self.lap_week.get():
                try:
                    if date.fromisoformat(r[1]).isocalendar()[1] != cur_week:
                        continue
                except ValueError:
                    continue
            self.lap_tree.insert("", "end", values=(r[0], r[1], r[2], r[3], r[4], r[5], r[6], rupiah(r[7])))
            tot += r[7] or 0
            n += 1
        self.lap_total.set(f"{n} baris  |  Total: {rupiah(tot)}")

    def lap_del(self):
        sel = self.lap_tree.selection()
        if not sel:
            popup_info(self, "Pilih Dulu", "Klik salah satu baris laporan dulu.")
            return
        v = self.lap_tree.item(sel[0], "values")
        if not popup_confirm(self, "Hapus Record", f"Hapus record #{v[0]} ({v[2]}, {v[7]})?"):
            return
        con = db()
        try:
            con.execute("DELETE FROM records WHERE id=?", (v[0],))
            con.commit()
        finally:
            con.close()
        self.refresh_all()

    def export_csv(self):
        con = db()
        try:
            rows = con.execute("""SELECT r.id, r.tanggal, e.nama, e.jabatan, r.jam_normal, r.jam_lembur,
                                  r.jam_libur, r.menit, r.total FROM records r
                                  LEFT JOIN employees e ON e.id=r.employee_id ORDER BY r.id DESC""").fetchall()
        finally:
            con.close()
        if not rows:
            popup_info(self, "Kosong", "Belum ada data untuk di-export.")
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
        popup_ok(self, "Selesai", f"{len(rows)} baris tersimpan ke:\n{p}")

    def backup_db(self):
        import shutil
        p = filedialog.asksaveasfilename(defaultextension=".db", filetypes=[("SQLite", "*.db")],
                                         initialfile=f"payroll_backup_{date.today().isoformat()}.db")
        if not p:
            return
        db()  # pastikan file ada
        shutil.copy(DB_FILE, p)
        popup_ok(self, "Backup Selesai", f"Database tersalin ke:\n{p}")

    # ----- pengaturan -----
    def _build_set(self):
        t = self.tabs["set"]
        ttk.Label(t, text="Pengaturan Perhitungan", style="Title.TLabel").pack(anchor="w", padx=12, pady=(12, 4))
        frm = ttk.Frame(t)
        frm.pack(fill="x", padx=12, pady=8)
        self.s_vars = {}
        self.s_err = ttk.Label(t, text="", style="Error.TLabel")
        fields = [("upah_per_jam", "Upah default per jam (Rp)"), ("jam_per_hari", "Jam kerja normal / hari"),
                  ("hari_per_minggu", "Hari kerja / minggu"), ("rate_lembur", "Rate lembur (x)"),
                  ("rate_libur", "Rate lembur hari libur (x)"), ("pembulatan_menit", "Pembulatan menit ke atas")]
        for i, (k, lbl) in enumerate(fields):
            ttk.Label(frm, text=lbl + ":").grid(row=i, column=0, sticky="w", pady=6)
            sv = tk.StringVar(value=str(self.settings[k]))
            sv.trace_add("write", lambda *a: self._validate_set())
            ttk.Entry(frm, textvariable=sv, width=16).grid(row=i, column=1, sticky="w", pady=6, padx=8)
            self.s_vars[k] = sv
        self.btn_set = ttk.Button(frm, text="Simpan Pengaturan", style="Primary.TButton",
                                  command=self.save_set)
        self.btn_set.grid(row=len(fields), column=1, sticky="w", pady=12)
        self._validate_set()

    def _validate_set(self):
        bad = False
        for k, sv in self.s_vars.items():
            v = parse_angka(sv.get())
            if v is None or v <= 0 or (k in ("hari_per_minggu", "pembulatan_menit") and not float(v).is_integer()):
                bad = True
        self.s_err.config(text="" if not bad else "Semua nilai harus angka positif (hari & menit bilangan bulat).")
        try:
            self.btn_set.config(state="disabled" if bad else "normal")
        except (tk.TclError, AttributeError):
            pass
        return not bad

    def save_set(self):
        if not self._validate_set():
            popup_error(self, "Belum Benar", "Perbaiki nilai yang belum valid dulu.")
            return
        ns = {}
        for k, sv in self.s_vars.items():
            v = parse_angka(sv.get())
            if v is None:
                v = 0
            ns[k] = int(v) if k in ("hari_per_minggu", "pembulatan_menit") else v
        self.settings = ns
        save_settings(ns)
        self._live()
        self.status.set("Pengaturan tersimpan.")
        popup_ok(self, "Tersimpan", "Pengaturan berhasil disimpan.\nHasil hitung ikut diperbarui.")

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
        try:
            nk = con.execute("SELECT COUNT(*) FROM employees WHERE aktif=1").fetchone()[0]
            rows = con.execute("SELECT jam_normal,jam_lembur,jam_libur,total,tanggal FROM records").fetchall()
            last = con.execute("""SELECT r.tanggal, e.nama, r.total FROM records r
                                  LEFT JOIN employees e ON e.id=r.employee_id
                                  ORDER BY r.id DESC LIMIT 5""").fetchall()
        finally:
            con.close()
        week = date.today().isocalendar()[1]
        tj = tg = 0.0
        for r in rows:
            try:
                if date.fromisoformat(r[4]).isocalendar()[1] == week:
                    tj += (r[0] or 0) + (r[1] or 0) + (r[2] or 0)
                    tg += r[3] or 0
            except (ValueError, TypeError):
                continue
        self.dash_vars["karyawan"].set(str(nk))
        self.dash_vars["jam"].set(f"{tj:.1f} jam")
        self.dash_vars["gaji"].set(rupiah(tg))
        for i in self.dash_tree.get_children():
            self.dash_tree.delete(i)
        for r in last:
            self.dash_tree.insert("", "end", values=(r[0], r[1], rupiah(r[2])))


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
