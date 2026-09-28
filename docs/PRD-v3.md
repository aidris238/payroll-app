# PRD — PayrollPro v3 (GUI Desktop)

Tanggal: 2026-09-28
Status: aktif — menggantikan versi CLI (payroll.py) dan GUI v2 (tab dasar).

## 1. Ringkasan
Aplikasi desktop Windows/Linux untuk hitung gaji mingguan karyawan.
Gaji = pokok + lembur + lembur libur, dengan pembulatan menit ke atas.
Target user: admin/owner non-teknis. Satu file EXE, double-click jalan,
tanpa install Python, data tersimpan lokal (SQLite di folder aplikasi).

## 2. Masalah yang diperbaiki dari v2
1. Popup masih messagebox standar, tidak konsisten & tidak centered.
2. Hasil hitung cuma label polos — tidak ada slip gaji yang bisa dicetak.
3. Bug: combobox karyawan bind ke `_hitung_autofill` yang tidak ada → crash saat pilih.
4. DB/settings path memakai `__file__` — rusak saat frozen (PyInstaller `_MEIPASS`).
5. Tidak ada validasi inline; error baru ketahuan setelah klik Simpan.
6. Laporan tidak bisa cari/filter; dashboard tidak menampilkan transaksi terakhir.
7. Tidak ada cara mudah jalan dari source (run.bat/run.sh) dan README masih CLI lama.

## 3. Ruang lingkup v3
Masuk:
- 5 tab: Dashboard, Data Karyawan, Hitung Gaji, Laporan, Pengaturan.
- Popup custom: info / error / konfirmasi / slip gaji (semua modal, centered, styled).
- Slip gaji: teks monospace rapi, tombol Salin Total, Simpan .txt, Simpan ke Laporan.
- Hitung live (setiap ketikan langsung update hasil, tanpa klik).
- Format Rupiah otomatis (titik ribuan) di kolom upah & hasil.
- Validasi inline: field merah + pesan di bawah form, tombol nonaktif bila invalid.
- Laporan: kolom cari nama, filter minggu ini, footer total, export CSV, hapus baris.
- Dashboard: 3 kartu + tabel 5 transaksi terakhir.
- DB SQLite + settings.json di folder EXE (bukan temp), tombol Backup DB.
- Stdlib only (tkinter/sqlite3/csv/json) — nol dependency, build kecil & cepat.

Tidak masuk (nanti):
- Multi-user/login, absensi harian, PPh21/BPJS, cetak PDF, sync cloud.

## 4. Aturan hitung (tidak berubah)
- jam_std = jam_per_hari × hari_per_minggu
- normal_dibayar = min(jam_normal, jam_std); lebih = max(0, jam_normal − jam_std)
- menit_jam = ceil(menit / pembulatan) × (pembulatan/60)
- total_lembur = lebih + jam_lembur + menit_jam
- pokok = normal_dibayar × upah; lembur = total_lembur × upah × rate_lembur
- libur = jam_libur × upah × rate_libur; total = pokok + lembur + libur

## 5. Kriteria terima (harus lolos semua sebelum release)
1. `python -m py_compile payroll_gui.py` sukses.
2. Test logika (`python tests_smoke.py`): 5 kasus hitung + rupiah + DB roundtrip lolos.
3. GUI smoke: aplikasi terbuka tanpa exception (xvfb di Linux / langsung di Windows).
4. Pilih karyawan di combobox → tidak crash, upah terisi otomatis.
5. Hitung → popup slip muncul, format rapi, tombol Salin/Simpan bekerja.
6. Input negatif/huruf → field merah + popup error yang jelas, tidak crash.
7. Laporan: tambah → muncul; cari → filter benar; export CSV → file ada & bisa dibuka Excel.
8. EXE Windows hasil CI bisa dibuka di PC tanpa Python (tidak ada error python311.dll).
9. Cara jalan tertulis di README & terbukti: `run.bat` / `run.sh` / `python payroll_gui.py`.

## 6. Cara jalan (user)
- Windows: download `PayrollPro.exe` → double-click. Data (`payroll.db`) dibuat otomatis di folder yang sama.
- Dari source: `python payroll_gui.py` (butuh Python 3.10+, tanpa pip install).
- Alternatif cepat: `run.bat` (Windows) / `run.sh` (Linux).

## 7. File
- `payroll_gui.py` — aplikasi (satu file).
- `payroll_gui.spec` — build Windows (console=False, strip=False).
- `docs/PRD-v3.md` — file ini.
- `tests_smoke.py` — test logika + DB (tanpa GUI).
- `run.bat`, `run.sh` — jalan cepat dari source.
- `README.md` — diperbarui ke edisi GUI.
