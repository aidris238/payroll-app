# 📊 Aplikasi Penggajian Karyawan (Mingguan)

Aplikasi CLI modern untuk menghitung gaji mingguan karyawan dengan dukungan lembur, lembur hari libur, dan pembulatan menit ke atas.

![Preview](https://img.shields.io/badge/Python-3.8+-blue) ![Rich](https://img.shields.io/badge/UI-Rich-ff69b4) ![License](https://img.shields.io/badge/License-MIT-green)

---

## ✨ Fitur

| Fitur | Deskripsi |
|-------|-----------|
| 💰 **Gaji Pokok** | Upah normal per jam × jam kerja standar |
| ⏰ **Lembur Biasa** | Jam di luar jam normal (rate 1.5x default) |
| 🎉 **Lembur Hari Libur** | Jam kerja di hari libur (rate 2.0x default) |
| 🔢 **Pembulatan Menit** | Menit tambahan dibulatkan ke atas (default 15 menit = 0.25 jam) |
| ⚙️ **Konfigurasi Fleksibel** | Upah/jam, jam/hari, hari/minggu, rate lembur semua bisa diubah |
| 📊 **Tampilan Modern** | Rich UI: tabel warna, panel, ringkasan 3-kolom |
| 💾 **Export JSON** | Hasil otomatis tersimpan ke `payroll_result.json` |
| 🔁 **Multi-karyawan** | Hitung berulang untuk banyak karyawan |

---

## 🚀 Quick Start

### 1. Clone & Install
```bash
git clone https://github.com/aidris238/payroll-app.git
cd payroll-app
pip install rich
```

### 2. Jalankan
```bash
python payroll.py
```

### 3. Build EXE (Windows/Linux)
```bash
pip install pyinstaller
pyinstaller --onefile --strip --optimize=2 --name payroll payroll.py
# Hasil: dist/payroll (Linux) / dist/payroll.exe (Windows)
```

---

## 📋 Contoh Penggunaan

```
╔══════════════════════════════╗
║ APLIKASI PENGGAJIAN KARYAWAN ║
╚═ Perhitungan Mingguan • Lemb═╝

───────────────────────────── ⚙️  KONFIGURASI UPAH ─────────────────────────────
Upah per jam (50000.0): 50000
Jam kerja normal per hari (8.0): 8
Hari kerja per minggu (6): 6
Pembulatan menit ke atas (menit) (15): 15

─────────────────────────── 📋 JAM KERJA MINGGU INI ────────────────────────────
Jam normal standar per minggu: 48.0 jam (6 hari × 8.0 jam)
Jam kerja normal (total mingguan) (48.0): 48
Jam lembur (di luar jam normal) (0.0): 5
Jam lembur hari libur (0.0): 0
Menit tambahan (akan dibulatkan ke atas) (0): 30

────────────────────────────────── 💰 HASIL PERHITUNGAN ──────────────────────────────────

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Keterangan                          ┃ Jumlah                 ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━┩
│ Gaji Pokok                          │ Rp 2.400.000           │
│ Gaji Lembur                         │ Rp 412.500             │
│ Gaji Lembur Libur                   │ Rp 0                   │
├──────────────────────────────────────┼────────────────────────┤
│ TOTAL GAJI                          │ Rp 2.812.500           │
└──────────────────────────────────────┴────────────────────────┘

💵 Total        ⏱️ Jam          📊 Avg
Rp 2.812.500    53.0 jam        Rp 53.066/jam

✓ Hasil disimpan ke payroll_result.json
```

---

## 🧮 Rumus Perhitungan

```
Jam Normal Mingguan = Jam/Hari × Hari/Minggu

Jam Normal Dibayar = min(Jam Normal Input, Jam Normal Mingguan)
Jam Lebih = max(0, Jam Normal Input - Jam Normal Mingguan)

Menit Dibulatkan = ceil(Menit Tambahan / Pembulatan) × (Pembulatan/60)
Jam Lembur Total = Jam Lebih + Jam Lembur Input + Menit Dibulatkan

Gaji Pokok = Jam Normal Dibayar × Upah/Jam
Gaji Lembur = Jam Lembur Total × Upah/Jam × Rate Lembur
Gaji Lembur Libur = Jam Lembur Libur × Upah/Jam × Rate Libur

TOTAL = Gaji Pokok + Gaji Lembur + Gaji Lembur Libur
```

---

## 📁 Struktur Repo

```
payroll-app/
├── payroll.py          # Source code utama (Rich CLI)
├── payroll.spec        # PyInstaller spec
├── dist/payroll        # Executable Linux (14 MB)
├── build/              # Build artifacts (gitignored)
├── payroll_result.json # Output terakhir (gitignored)
└── README.md
```

---

## 🛠️ Teknologi

- **Python 3.8+**
- **Rich** — Terminal formatting, tables, panels, prompts
- **PyInstaller** — Single-file executable build
- **Dataclasses** — Type-safe config & result objects

---

## 📝 Lisensi

MIT License — bebas digunakan, dimodifikasi, dan didistribusikan.

---

## 🤝 Kontribusi

PR welcome! Ide:
- Export ke CSV/Excel
- Simpan history karyawan
- GUI versi (Tkinter/PyQt)
- Dukungan shift pagi/siang/malam

---

> Dibuat untuk mempermudah perhitungan gaji mingguan dengan standar Indonesia.