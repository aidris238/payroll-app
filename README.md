# PayrollPro — Penggajian Karyawan Mingguan (GUI Desktop)

Aplikasi desktop profesional untuk menghitung gaji mingguan: pokok + lembur +
lembur hari libur, dengan pembulatan menit ke atas. Data tersimpan lokal (SQLite).

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Stdlib](https://img.shields.io/badge/Deps-stdlib_only-green)
![License](https://img.shields.io/badge/License-MIT-green)

## Cara pakai (pilih satu)

**Windows — tanpa install apa pun:**
1. Buka halaman [Releases](../../releases), download `PayrollPro.exe`.
2. Double-click. Selesai. (`payroll.db` dibuat otomatis di folder yang sama.)

**Linux:**
1. Download `PayrollPro`, lalu `chmod +x PayrollPro && ./PayrollPro` (butuh X server).

**Dari source (semua OS, tanpa pip install):**
```bash
python payroll_gui.py
# atau Windows: run.bat | Linux/macOS: ./run.sh
```
Butuh Python 3.10+ (sudah termasuk tkinter di installer standar).

## Alur kerja

1. **Data Karyawan** — tambah nama + upah/jam (dialog popup, validasi inline).
2. **Hitung Gaji** — pilih karyawan, isi jam & menit. Hasil terhitung
   otomatis setiap ketikan. Klik "Tampilkan Slip" untuk slip gaji rapi
   (bisa salin total, simpan .txt, atau langsung simpan ke laporan).
3. **Laporan** — cari nama, filter minggu ini, hapus baris, export CSV (buka di Excel).
4. **Pengaturan** — ubah upah default, jam/hari, hari/minggu, rate lembur,
   rate libur, pembulatan menit.
5. **Dashboard** — kartu ringkasan + 5 transaksi terakhir.

Menu: File (Export CSV, Backup Database, Keluar) · Karyawan · Bantuan (Cara Pakai, Tentang).

## Rumus

```
jam_std        = jam_per_hari × hari_per_minggu
normal_dibayar = min(jam_normal, jam_std)
lebih          = max(0, jam_normal − jam_std)
menit_jam      = ceil(menit / pembulatan) × (pembulatan/60)
total_lembur   = lebih + jam_lembur + menit_jam
pokok  = normal_dibayar × upah
lembur = total_lembur × upah × rate_lembur
libur  = jam_libur × upah × rate_libur
TOTAL  = pokok + lembur + libur
```

## File

```
payroll_gui.py    # aplikasi (satu file, stdlib only)
payroll_gui.spec  # build Windows (windowed, strip=False)
tests_smoke.py    # test logika + DB  → python tests_smoke.py
tests_gui.py      # test GUI headless  → python tests_gui.py
run.bat / run.sh  # jalan cepat dari source
docs/PRD-v3.md    # PRD aktif
payroll.py        # CLI lama (arsip, tidak dikembangkan)
```

## Build EXE dari source

```bash
pip install pyinstaller
pyinstaller payroll_gui.spec        # Windows → dist/PayrollPro.exe
pyinstaller --onefile --optimize=1 --name PayrollPro payroll_gui.py   # Linux
```
Rilis resmi dibuat otomatis oleh GitHub Actions setiap push tag `v*`.

## Lisensi

MIT — bebas dipakai, diubah, disebar.
