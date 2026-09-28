#!/usr/bin/env python3
"""PayrollPro v4 - Aplikasi Penggajian Karyawan Mingguan (GUI Desktop).
Stdlib only: tkinter + sqlite3 + csv + json. Lihat docs/PRD-v4.md.
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
APP_VERSION = "v4.0"

# Font lintas OS (Segoe UI tidak ada di Linux).
if sys.platform.startswith("win"):
    FONT, MONO = "Segoe UI", "Consolas"
else:
    FONT, MONO = "DejaVu Sans", "DejaVu Sans Mono"


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


def fmt_ribu(x) -> str:
    """50000 -> '50.000'. Integer-safe (tanpa float agar presisi)."""
    try:
        s = str(int(round(float(str(x).strip()))))
    except (ValueError, TypeError, AttributeError):
        return "0"
    neg = s.startswith("-")
    s = s.lstrip("-")
    parts = []
    while len(s) > 3:
        parts.append(s[-3:])
        s = s[:-3]
    parts.append(s)
    return ("-" if neg else "") + ".".join(reversed(parts))


def fmt_des(x, nd=2) -> str:
    """5.5 -> '5,5' (koma Indonesia), trailing nol dibuang."""
    try:
        v = float(x)
    except (ValueError, TypeError):
        return "0"
    s = f"{v:.{nd}f}".rstrip("0").rstrip(".")
    return s.replace(".", ",") if s else "0"


def rupiah(x) -> str:
    return f"Rp {fmt_ribu(x)}"


def parse_angka(txt: str):
    """Terima '50.000', '50000', 'Rp 50.000', '8,5', '8.5', '1.234,5' -> float."""
    if txt is None:
        return None
    t = str(txt).strip().replace("Rp", "").replace(" ", "")
    if not t or t in ("-", ",", "."):
        return None
    neg = t.startswith("-")
    t = t.lstrip("-")
    if "," in t and "." in t:
        t = t.replace(".", "").replace(",", ".")  # 1.234,5 -> 1234.5
    elif "," in t:
        t = t.replace(",", ".")  # 8,5 -> 8.5
    elif t.count(".") > 1:
        t = t.replace(".", "")  # 50.000.000 -> 50000000
    elif t.count(".") == 1:
        # Satu titik ambigu: "50.000" (ribuan ID) vs "8.5" (desimal).
        int_part, frac_part = t.split(".")
        if len(frac_part) == 3 and int_part and int_part.isdigit():
            t = int_part + frac_part
    try:
        v = float(t)
    except ValueError:
        return None
    return -v if neg else v


def iso_week_key(tanggal: str):
    """'2026-09-28' -> (2026, 40). Dipakai agar minggu tidak campur antar tahun."""
    d = date.fromisoformat(tanggal)
    iso = d.isocalendar()
    return (iso[0], iso[1])


# ---------------- popup: selalu tengah, tidak pernah kiri-atas ----------------

def center_modal(win: tk.Toplevel, parent, width=None, height=None):
    """Posisikan window TEPAT di tengah parent (atau layar). Wajib dipanggil
    saat window masih withdraw agar Windows WM menghormati geometrinya."""
    win.withdraw()
    win.update_idletasks()
    w = width or win.winfo_reqwidth()
    h = height or win.winfo_reqheight()
    try:
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        if pw < 50 or ph < 50:  # parent belum di-layout -> tengah layar
            x, y = (sw - w) // 2, (sh - h) // 2
        else:
            x, y = px + (pw - w) // 2, py + (ph - h) // 2
        x = max(0, min(x, sw - w - 10))
        y = max(0, min(y, sh - h - 40))
    except tk.TclError:
        x, y = 80, 80
    win.geometry(f"{w}x{h}+{x}+{y}")
    win.update_idletasks()
    win.deiconify()
    win.lift()
    try:
        win.focus_force()
    except tk.TclError:
        pass


class Popup(tk.Toplevel):
    """Popup modal generik: judul + ikon + pesan + tombol. Selalu tengah."""

    ICONS = {"info": ("\u2139", "#2563EB"), "ok": ("\u2714", "#16A34A"),
             "warn": ("\u26a0", "#D97706"), "error": ("\u2716", "#DC2626")}

    def __init__(self, parent, title, message, kind="info", buttons=("OK",), width=440):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.transient(parent)
        self.result = None
        glyph, color = self.ICONS.get(kind, self.ICONS["info"])

        head = ttk.Frame(self, padding=(18, 14, 18, 4))
        head.pack(fill="x")
        tk.Label(head, text=glyph, font=(FONT, 22, "bold"), fg=color,
                 bg=self._bg()).pack(side="left", padx=(0, 12))
        tk.Label(head, text=title, font=(FONT, 12, "bold")).pack(side="left", anchor="w")

        tk.Label(self, text=message, font=(FONT, 10), justify="left",
                 wraplength=width - 40, anchor="w").pack(fill="x", padx=18, pady=(4, 8))

        bar = ttk.Frame(self, padding=(18, 4, 18, 14))
        bar.pack(fill="x")
        for i, b in enumerate(buttons):
            ttk.Button(bar, text=b, style="Primary.TButton" if i == 0 else "TButton",
                       command=lambda v=b: self._close(v)).pack(side="right", padx=(8, 0))
        self.bind("<Return>", lambda e: self._close(buttons[0]))
        self.bind("<Escape>", lambda e: self._close(None))
        self.protocol("WM_DELETE_WINDOW", lambda: self._close(None))
        center_modal(self, parent, width)
        self.grab_set()
        self.wait_window(self)

    def _bg(self):
        try:
            return self.cget("background")
        except tk.TclError:
            return "SystemButtonFace"

    def _close(self, v):
        self.result = v
        try:
            self.grab_release()
        except tk.TclError:
            pass
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
    """Popup slip gaji: tengah layar, teks monospace rapi + tombol aksi."""

    def __init__(self, parent, body, total_str, on_save_report, on_save_txt):
        super().__init__(parent)
        self.title("Slip Gaji Mingguan")
        self.resizable(True, True)
        self.transient(parent)
        head = ttk.Frame(self, padding=(16, 12, 16, 4))
        head.pack(fill="x")
        tk.Label(head, text="\U0001f9fe", font=(FONT, 20)).pack(side="left", padx=(0, 10))
        tk.Label(head, text="Slip Gaji Mingguan", font=(FONT, 12, "bold")).pack(side="left")
        tk.Label(head, text=total_str, font=(FONT, 12, "bold"), fg="#1E40AF").pack(side="right")
        txt = tk.Text(self, font=(MONO, 10), width=54, height=19,
                      relief="solid", borderwidth=1, padx=10, pady=10)
        txt.insert("1.0", body)
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
        center_modal(self, parent, 520, 560)
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
    L = 42
    g = [f"SLIP GAJI MINGGUAN", f"Tanggal: {tanggal}", "-" * L,
         f"Karyawan : {nama}", f"Upah/jam : {rupiah(upah)}", "-" * L,
         f"Gaji pokok        : {rupiah(r['pokok']):>15}",
         f"  ({fmt_des(r['normal_dibayar'], 1)} jam normal)",
         f"Gaji lembur       : {rupiah(r['lembur']):>15}",
         f"  ({fmt_des(r['jam_lembur_total'])} jam)",
         f"Gaji lembur libur : {rupiah(r['libur']):>15}",
         f"  ({fmt_des(vals['jam_libur'], 1)} jam libur)", "-" * L,
         f"TOTAL             : {rupiah(r['total']):>15}", "-" * L,
         f"Rincian: normal {fmt_des(vals['jam_normal'], 1)}j,",
         f"lembur {fmt_des(vals['jam_lembur'], 1)}j, libur {fmt_des(vals['jam_libur'], 1)}j,",
         f"menit {menit} -> {fmt_des(r['menit_jam'])}j"]
    return "\n".join(g)


# ---------------- entry pintar: format otomatis + validasi ----------------

class _BaseEntry(ttk.Entry):
    """Base: StringVar sendiri + flag anti-loop + style invalid + pesan error."""

    def __init__(self, master, value="", width=16, **kw):
        self.var = tk.StringVar(value=value)
        super().__init__(master, textvariable=self.var, width=width, **kw)
        self._busy = False
        self.bind("<KeyRelease>", lambda e: self._on_type())
        self.bind("<FocusOut>", lambda e: self._on_focus_out())

    def mark(self, ok: bool):
        try:
            self.config(style="TEntry" if ok else "Invalid.TEntry")
        except tk.TclError:
            pass

    def _caret_digits(self):
        """Jumlah digit di kiri kursor (untuk pengembalian posisi)."""
        try:
            pos = self.index(tk.INSERT)
        except tk.TclError:
            pos = len(self.var.get())
        return len([c for c in self.var.get()[:pos] if c.isdigit()])

    def _restore_caret(self, digits_before):
        txt = self.var.get()
        if digits_before <= 0:
            self.icursor(0)
            return
        n, newpos = 0, len(txt)
        for i, c in enumerate(txt):
            if c.isdigit():
                n += 1
                if n >= digits_before:
                    newpos = i + 1
                    break
        try:
            self.icursor(newpos)
        except tk.TclError:
            pass

    def _on_type(self):
        pass

    def _on_focus_out(self):
        pass


class MoneyEntry(_BaseEntry):
    """Rupiah integer: ketik 50000 -> tampil 50.000 otomatis. valid() -> int/None."""

    def __init__(self, master, value="", **kw):  # type: ignore[no-untyped-def]
        init = fmt_ribu(value) if str(value).strip() not in ("", "0", "0.0") else (str(value).strip() or "")
        super().__init__(master, value=init, **kw)
        try:
            self.config(justify="right")
        except tk.TclError:
            pass

    def _on_type(self):
        if self._busy:
            return
        self._busy = True
        try:
            before = self._caret_digits()
            digits = "".join(c for c in self.var.get() if c.isdigit())[:15]
            if not digits:
                self.var.set("")
                return
            num = digits.lstrip("0") or "0"
            self.var.set(fmt_ribu(int(num)))
            self._restore_caret(before)
        finally:
            self._busy = False

    def _on_focus_out(self):
        self._on_type()  # pastikan rapi saat keluar field

    def valid(self):
        d = "".join(c for c in self.var.get() if c.isdigit())
        return int(d) if d else None


class IntEntry(_BaseEntry):
    """Bilangan bulat >= 0 (menit, hari). valid() -> int/None."""

    def _on_type(self):
        if self._busy:
            return
        self._busy = True
        try:
            before = self._caret_digits()
            digits = "".join(c for c in self.var.get() if c.isdigit())[:6]
            self.var.set(digits)
            self._restore_caret(before)
        finally:
            self._busy = False

    def _on_focus_out(self):
        self._on_type()

    def valid(self):
        t = self.var.get().strip()
        return int(t) if t.isdigit() else None


class DecEntry(_BaseEntry):
    """Desimal >= 0 (jam, rate). Tampil koma ID saat keluar field. valid() -> float/None."""

    def _on_focus_out(self):
        v = parse_angka(self.var.get())
        if v is None:
            return
        self.var.set(fmt_des(v, 2))

    def valid(self):
        return parse_angka(self.var.get())


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


# ---------------- aplikasi ----------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_TITLE} {APP_VERSION}")
        self.minsize(920, 600)
        self.settings = load_settings()
        self._unsaved = False  # ada hitungan yang belum disimpan
        self._style()
        self._menu()
        self._banner()
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(0, 10))
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
        self.refresh_all(first=True)
        # status bar: pesan kiri + info kanan
        bar = ttk.Frame(self, padding=(10, 0, 10, 8))
        bar.pack(fill="x")
        self.status = tk.StringVar(value="Siap.")
        ttk.Label(bar, textvariable=self.status, style="Status.TLabel").pack(side="left")
        self.status_right = tk.StringVar()
        ttk.Label(bar, textvariable=self.status_right, style="Status.TLabel").pack(side="right")
        self._update_status_right()
        # window utama juga dibuka di tengah layar
        self.withdraw()
        self.update_idletasks()
        w, h = 1020, 680
        try:
            sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
            self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2 - 20}")
        except tk.TclError:
            self.geometry(f"{w}x{h}")
        self.deiconify()
        # shortcut enterprise
        self.bind("<F5>", lambda e: self.refresh_all())
        self.bind("<Control-s>", lambda e: self._shortcut_save())
        self.bind("<Control-S>", lambda e: self._shortcut_save())
        self.bind("<Control-e>", lambda e: self.export_csv())
        self.bind("<Control-E>", lambda e: self.export_csv())
        self.protocol("WM_DELETE_WINDOW", self.on_exit)

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
        st.configure("TLabel", background=BG, font=(FONT, 10))
        st.configure("Title.TLabel", font=(FONT, 16, "bold"), foreground=DARK)
        st.configure("Card.TFrame", background="white", relief="solid", borderwidth=1)
        st.configure("Card.TLabel", background="white")
        st.configure("TButton", font=(FONT, 10), padding=6)
        st.configure("Primary.TButton", background=P, foreground="white")
        st.map("Primary.TButton", background=[("active", DARK)])
        st.configure("TEntry", fieldbackground="white")
        st.configure("Invalid.TEntry", fieldbackground="#FEE2E2", foreground="#991B1B")
        st.configure("Treeview", font=(FONT, 10), rowheight=28)
        st.configure("Treeview.Heading", font=(FONT, 10, "bold"))
        st.configure("Status.TLabel", font=(FONT, 9), foreground="#475569")
        st.configure("Error.TLabel", background=BG, font=(FONT, 9), foreground="#DC2626")

    def _banner(self):
        b = tk.Frame(self, bg="#1E40AF", height=54)
        b.pack(fill="x")
        b.pack_propagate(False)
        tk.Label(b, text="\U0001f4ca  PayrollPro", bg="#1E40AF", fg="white",
                 font=(FONT, 14, "bold")).pack(side="left", padx=14)
        tk.Label(b, text="Penggajian Mingguan  •  Lembur  •  Pembulatan Menit",
                 bg="#1E40AF", fg="#BFDBFE", font=(FONT, 9)).pack(side="left")
        week = date.today().isocalendar()
        tk.Label(b, text=f"{APP_VERSION}   |   Minggu ke-{week[1]}/{week[0]}",
                 bg="#1E40AF", fg="#BFDBFE", font=(FONT, 9)).pack(side="right", padx=14)

    def _menu(self):
        m = tk.Menu(self)
        self.config(menu=m)
        f = tk.Menu(m, tearoff=0)
        f.add_command(label="Export Laporan ke CSV...", command=self.export_csv)
        f.add_command(label="Backup Database...", command=self.backup_db)
        f.add_separator()
        f.add_command(label="Keluar", command=self.on_exit)
        m.add_cascade(label="File", menu=f)
        k = tk.Menu(m, tearoff=0)
        k.add_command(label="Tambah Karyawan...", command=self.emp_add)
        k.add_command(label="Refresh Semua  (F5)", command=self.refresh_all)
        m.add_cascade(label="Karyawan", menu=k)
        h = tk.Menu(m, tearoff=0)
        h.add_command(label="Cara Pakai...", command=self.help_dialog)
        h.add_command(label="Tentang...", command=lambda: popup_info(
            self, "Tentang", f"{APP_TITLE} {APP_VERSION}\nGaji mingguan + lembur + pembulatan menit.\nData tersimpan lokal (SQLite)."))
        m.add_cascade(label="Bantuan", menu=h)

    def on_exit(self):
        if self._unsaved and not popup_confirm(
                self, "Belum Disimpan",
                "Ada hasil perhitungan yang belum disimpan ke Laporan.\nTetap keluar?",
                ok_label="Tetap Keluar"):
            return
        self.destroy()

    def _shortcut_save(self):
        try:
            if str(self.notebook.select()) == str(self.tabs["hitung"]):
                self.do_simpan()
            elif str(self.notebook.select()) == str(self.tabs["set"]):
                self.save_set()
        except tk.TclError:
            pass

    def _update_status_right(self):
        try:
            self.status_right.set(f"DB: {os.path.basename(DB_FILE)}")
        except tk.TclError:
            pass

    def help_dialog(self):
        popup_info(self, "Cara Pakai",
                   "1. Tab Data Karyawan: tambah nama + upah/jam.\n"
                   "     Angka upah otomatis bertitik (50.000) saat mengetik.\n"
                   "2. Tab Hitung Gaji: pilih karyawan, isi jam & menit.\n"
                   "     Hasil terhitung otomatis, klik Slip / Simpan (Ctrl+S).\n"
                   "3. Tab Laporan: cari, filter, klik judul kolom untuk urutkan.\n"
                   "4. Tab Pengaturan: ubah rate & jam standar.\n"
                   "Shortcut: F5 refresh  •  Ctrl+S simpan  •  Ctrl+E export CSV.")

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
                     font=(FONT, 20, "bold"), fg="#1E40AF").pack(anchor="w")
            self.dash_vars[key] = v
        btns = ttk.Frame(t)
        btns.pack(fill="x", padx=12)
        ttk.Button(btns, text="Refresh", command=self.refresh_all).pack(side="left")
        ttk.Button(btns, text="Hitung Gaji \u2192", style="Primary.TButton",
                   command=lambda: self.notebook.select(self.tabs["hitung"])).pack(side="left", padx=8)
        ttk.Label(t, text="5 Transaksi Terakhir:", font=(FONT, 11, "bold")).pack(anchor="w", padx=12, pady=(12, 4))
        cols = ("tanggal", "nama", "total")
        self.dash_tree = ttk.Treeview(t, columns=cols, show="headings", height=6)
        for c, tt, w in [("tanggal", "Tanggal", 130), ("nama", "Nama", 300), ("total", "Total", 180)]:
            self.dash_tree.heading(c, text=tt)
            self.dash_tree.column(c, width=w, anchor="e" if c == "total" else "w")
        self.dash_tree.tag_configure("odd", background="#F8FAFC")
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
        self.emp_tree.tag_configure("odd", background="#F8FAFC")
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
        for n, r in enumerate(self._emp_rows()):
            self.emp_tree.insert("", "end", values=(r[0], r[1], r[2], rupiah(r[3])),
                                 tags=("odd",) if n % 2 else ())

    def _emp_dialog(self, title, nama="", jabatan="", upah=""):  # type: ignore[no-untyped-def]
        d = tk.Toplevel(self)
        d.title(title)
        d.resizable(False, False)
        d.transient(self)
        ttk.Label(d, text="Nama *").grid(row=0, column=0, sticky="w", padx=14, pady=(14, 0))
        e_nama = ttk.Entry(d, width=34)
        e_nama.insert(0, nama)
        e_nama.grid(row=1, column=0, sticky="we", padx=14)
        err_nama = ttk.Label(d, text="", style="Error.TLabel")
        err_nama.grid(row=2, column=0, sticky="w", padx=14)
        ttk.Label(d, text="Jabatan").grid(row=3, column=0, sticky="w", padx=14, pady=(6, 0))
        e_jab = ttk.Entry(d, width=34)
        e_jab.insert(0, jabatan)
        e_jab.grid(row=4, column=0, sticky="we", padx=14)
        ttk.Label(d, text="Upah per jam (Rp) *  —  otomatis bertitik").grid(
            row=5, column=0, sticky="w", padx=14, pady=(6, 0))
        e_upah = MoneyEntry(d, value=upah if upah else "", width=34)
        e_upah.grid(row=6, column=0, sticky="we", padx=14)
        err_upah = ttk.Label(d, text="", style="Error.TLabel")
        err_upah.grid(row=7, column=0, sticky="w", padx=14)
        out = {}

        def validate():
            ok = True
            if not e_nama.get().strip():
                err_nama.config(text="Nama wajib diisi.")
                ok = False
            else:
                err_nama.config(text="")
            u = e_upah.valid()
            if u is None or u <= 0:
                err_upah.config(text="Upah harus angka lebih dari 0.")
                e_upah.mark(False)
                ok = False
            else:
                err_upah.config(text="")
                e_upah.mark(True)
            return ok

        def ok():
            if not validate():
                return
            out.update(nama=e_nama.get().strip(), jabatan=e_jab.get().strip(),
                       upah=e_upah.valid())
            d.destroy()

        btns = ttk.Frame(d)
        btns.grid(row=8, column=0, sticky="e", padx=14, pady=16)
        ttk.Button(btns, text="Batal", command=d.destroy).pack(side="right")
        ttk.Button(btns, text="Simpan", style="Primary.TButton", command=ok).pack(side="right", padx=8)
        d.bind("<Return>", lambda e: ok())
        d.bind("<Escape>", lambda e: d.destroy())
        d.protocol("WM_DELETE_WINDOW", d.destroy)
        center_modal(d, self, 400)
        e_nama.focus_set()
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
        r = self._emp_dialog("Ubah Karyawan", nama, jab, str(parse_angka(upah_txt) or ""))
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
        fields = [("jam_normal", "Jam normal minggu ini", DecEntry, "48"),
                  ("jam_lembur", "Jam lembur", DecEntry, "0"),
                  ("jam_libur", "Jam lembur hari libur", DecEntry, "0"),
                  ("menit", "Menit tambahan", IntEntry, "0")]
        for i, (k, lbl, cls, dflt) in enumerate(fields, start=1):
            ttk.Label(frm, text=lbl + ":").grid(row=i, column=0, sticky="w", pady=5)
            ent = cls(frm, value=dflt, width=14)
            ent.var.trace_add("write", lambda *a: self._live(user=True))
            ent.grid(row=i, column=1, sticky="w", pady=5, padx=8)
            err = ttk.Label(frm, text="", style="Error.TLabel")
            err.grid(row=i, column=2, sticky="w")
            self.h_inputs[k] = (ent.var, ent)
            self.h_errs[k] = err
        self.h_form_err = ttk.Label(t, text="", style="Error.TLabel")
        self.h_form_err.pack(anchor="w", padx=12)
        btns = ttk.Frame(t)
        btns.pack(fill="x", padx=12, pady=4)
        self.btn_slip = ttk.Button(btns, text="\U0001f9fe Tampilkan Slip", style="Primary.TButton",
                                   command=self.show_slip)
        self.btn_slip.pack(side="left", padx=(0, 8))
        self.btn_simpan = ttk.Button(btns, text="Simpan ke Laporan  (Ctrl+S)", command=self.do_simpan)
        self.btn_simpan.pack(side="left")
        res = ttk.Frame(t, style="Card.TFrame", padding=14)
        res.pack(fill="both", expand=True, padx=12, pady=12)
        tk.Label(res, text="Hasil Perhitungan (live)", bg="white",
                 font=(FONT, 12, "bold"), fg="#1E40AF").pack(anchor="w")
        self.h_result = tk.StringVar(value="Pilih karyawan dan isi jam kerja.")
        tk.Label(res, textvariable=self.h_result, bg="white",
                 font=(MONO, 11), justify="left").pack(anchor="w", pady=8)
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

    def _live(self, user=False):
        """Hitung ulang tiap ada perubahan; validasi inline. Tidak pernah popup."""
        for e in self.h_errs.values():
            e.config(text="")
        for _, ent in self.h_inputs.values():
            ent.mark(True)
        self.btn_slip.config(state="disabled")
        self.btn_simpan.config(state="disabled")
        self._last = None
        m = self._h_emp_map()
        key = self.h_emp.get()
        if key not in m:
            self.h_result.set("Belum ada karyawan.\nTambahkan dulu di tab Data Karyawan.")
            return
        vals, bad = {}, False
        for k, (_, ent) in self.h_inputs.items():
            v = ent.valid()
            if v is None or v < 0 or (k == "menit" and not float(v).is_integer()):
                self.h_errs[k].config(text="angka \u2265 0")
                ent.mark(False)
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
        if user:
            self._unsaved = True
        self.h_result.set(
            f"{nama}  ({rupiah(upah)}/jam)\n"
            f"Gaji pokok        : {rupiah(r['pokok'])}\n"
            f"Gaji lembur       : {rupiah(r['lembur'])}  ({fmt_des(r['jam_lembur_total'])} jam)\n"
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
        self._unsaved = False
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
        ttk.Button(bar, text="Export CSV...  (Ctrl+E)", command=self.export_csv).pack(side="right", padx=4)
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
        self._lap_sort = {"col": None, "rev": False}
        for c, tt, w in [("id", "ID", 45), ("tanggal", "Tanggal", 110), ("nama", "Nama", 200),
                         ("normal", "Normal", 75), ("lembur", "Lembur", 75), ("libur", "Libur", 75),
                         ("menit", "Menit", 65), ("total", "Total", 150)]:
            self.lap_tree.heading(c, text=tt)
            self.lap_tree.column(c, width=w,
                                 anchor="e" if c in ("normal", "lembur", "libur", "menit", "total") else "w")
        for sortable in ("tanggal", "nama", "total"):
            self.lap_tree.heading(sortable, command=lambda c=sortable: self._sort_lap(c))
        self.lap_tree.tag_configure("odd", background="#F8FAFC")
        self.lap_tree.pack(fill="both", expand=True, padx=12)
        self.lap_total = tk.StringVar(value="Total: Rp 0")
        ttk.Label(t, textvariable=self.lap_total, font=(FONT, 11, "bold")).pack(anchor="e", padx=12, pady=8)

    def _lap_base_rows(self):
        con = db()
        try:
            return con.execute("""SELECT r.id, r.tanggal, e.nama, r.jam_normal, r.jam_lembur,
                                  r.jam_libur, r.menit, r.total FROM records r
                                  LEFT JOIN employees e ON e.id=r.employee_id
                                  ORDER BY r.id DESC LIMIT 1000""").fetchall()
        finally:
            con.close()

    def refresh_lap(self):
        for i in self.lap_tree.get_children():
            self.lap_tree.delete(i)
        rows = self._filtered_rows()
        if self._lap_sort["col"]:
            rows = self._sorted(rows)
        for n, r in enumerate(rows):
            self.lap_tree.insert("", "end", values=(r[0], r[1], r[2], r[3], r[4], r[5], r[6], rupiah(r[7])),
                                 tags=("odd",) if n % 2 else ())
        tot = sum(r[7] or 0 for r in rows)
        self._paint_sort_heads()
        self.lap_total.set(f"{len(rows)} baris  |  Total: {rupiah(tot)}")

    def _filtered_rows(self):
        q = self.lap_q.get().strip().lower()
        only_week = self.lap_week.get()
        cur = iso_week_key(date.today().isoformat())
        out = []
        for r in self._lap_base_rows():
            if q and q not in (r[2] or "").lower():
                continue
            if only_week:
                try:
                    if iso_week_key(r[1]) != cur:
                        continue
                except ValueError:
                    continue
            out.append(r)
        return out

    def _sorted(self, rows):
        col, rev = self._lap_sort["col"], self._lap_sort["rev"]
        idx = {"tanggal": 1, "nama": 2, "total": 7}[col]
        if col == "total":
            key = lambda r: (r[7] or 0)
        else:
            key = lambda r: str(r[idx] or "").lower()
        return sorted(rows, key=key, reverse=rev)

    def _sort_lap(self, col):
        if self._lap_sort["col"] == col:
            self._lap_sort["rev"] = not self._lap_sort["rev"]
        else:
            self._lap_sort = {"col": col, "rev": False}
        self.refresh_lap()

    def _paint_sort_heads(self):
        base = {"id": "ID", "tanggal": "Tanggal", "nama": "Nama", "normal": "Normal",
                "lembur": "Lembur", "libur": "Libur", "menit": "Menit", "total": "Total"}
        for c, tt in base.items():
            arrow = ""
            if c == self._lap_sort["col"]:
                arrow = " \u25bc" if self._lap_sort["rev"] else " \u25b2"
            self.lap_tree.heading(c, text=tt + arrow)

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
        con = db()  # pastikan file + tabel ada
        con.close()
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
        fields = [("upah_per_jam", "Upah default per jam (Rp)", MoneyEntry),
                  ("jam_per_hari", "Jam kerja normal / hari", DecEntry),
                  ("hari_per_minggu", "Hari kerja / minggu", IntEntry),
                  ("rate_lembur", "Rate lembur (x)", DecEntry),
                  ("rate_libur", "Rate lembur hari libur (x)", DecEntry),
                  ("pembulatan_menit", "Pembulatan menit ke atas", IntEntry)]
        for i, (k, lbl, cls) in enumerate(fields):
            ttk.Label(frm, text=lbl + ":").grid(row=i, column=0, sticky="w", pady=6)
            ent = cls(frm, value=self.settings[k], width=16)
            ent.var.trace_add("write", lambda *a: self._validate_set())
            ent.grid(row=i, column=1, sticky="w", pady=6, padx=8)
            self.s_vars[k] = ent
        self.btn_set = ttk.Button(frm, text="Simpan Pengaturan  (Ctrl+S)", style="Primary.TButton",
                                  command=self.save_set)
        self.btn_set.grid(row=len(fields), column=1, sticky="w", pady=12)
        self.s_err.pack(anchor="w", padx=12, pady=(0, 8))
        self._validate_set()

    def _validate_set(self):
        bad = False
        for k, ent in self.s_vars.items():
            v = ent.valid()
            if v is None or v <= 0 or (k in ("hari_per_minggu", "pembulatan_menit")
                                      and not float(v).is_integer()):
                ent.mark(False)
                bad = True
            else:
                ent.mark(True)
        try:
            self.btn_set.config(state="disabled" if bad else "normal")
        except (tk.TclError, AttributeError):
            pass
        return not bad

    def save_set(self):
        if not self._validate_set():
            popup_error(self, "Belum Benar", "Perbaiki field bertanda merah dulu.")
            return
        ns = {}
        for k, ent in self.s_vars.items():
            v = ent.valid() or 0
            ns[k] = int(v) if k in ("hari_per_minggu", "pembulatan_menit") else v
        self.settings = ns
        save_settings(ns)
        self._live()
        self.status.set("Pengaturan tersimpan.")
        popup_ok(self, "Tersimpan", "Pengaturan berhasil disimpan.\nHasil hitung ikut diperbarui.")

    def refresh_set(self):
        for k, ent in self.s_vars.items():
            ent.var.set(fmt_ribu(self.settings[k]) if isinstance(ent, MoneyEntry)
                        else str(self.settings[k]))

    # ----- global -----
    def refresh_all(self, first=False):
        self.settings = load_settings()
        self.refresh_emp()
        self.refresh_hitung_combo()
        self.refresh_lap()
        if first and hasattr(self, "s_vars"):
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
        cur = iso_week_key(date.today().isoformat())
        tj = tg = 0.0
        for r in rows:
            try:
                if iso_week_key(r[4]) == cur:
                    tj += (r[0] or 0) + (r[1] or 0) + (r[2] or 0)
                    tg += r[3] or 0
            except (ValueError, TypeError):
                continue
        self.dash_vars["karyawan"].set(str(nk))
        self.dash_vars["jam"].set(f"{fmt_des(tj, 1)} jam")
        self.dash_vars["gaji"].set(rupiah(tg))
        for i in self.dash_tree.get_children():
            self.dash_tree.delete(i)
        for n, r in enumerate(last):
            self.dash_tree.insert("", "end", values=(r[0], r[1], rupiah(r[2])),
                                  tags=("odd",) if n % 2 else ())


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
