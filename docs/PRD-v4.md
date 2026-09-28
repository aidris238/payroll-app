# PRD — PayrollPro v4 (Enterprise Desktop)

Tanggal: 2026-09-28
Status: aktif — menggantikan v3. Fokus: popup selalu tengah, format angka otomatis, standar perusahaan.

## 1. Ringkasan
Aplikasi desktop Windows/Linux untuk gaji mingguan: pokok + lembur + lembur libur + pembulatan menit.
Satu file EXE, double-click jalan, tanpa Python, data lokal SQLite di folder aplikasi.
Target: admin non-teknis tapi kualitas enterprise (validasi, audit, backup, export).

## 2. Bug v3 yang diperbaiki di v4
1. Popup muncul kiri-atas: penyebab `SlipPopup` pakai `geometry("+px+60...")` dan dialog karyawan
   hitung posisi sebelum layout (winfo_width=1). Fix: helper `center_modal()` tunggal —
   withdraw dulu, ukur reqheight, tengah parent/layar, clamp ke layar, deiconify+lift+focus.
2. Angka tanpa titik otomatis: v3 entry polos. Fix: `MoneyEntry` (upah) format live
   `50000 -> 50.000` saat mengetik dengan posisi kursor dijaga; `IntEntry`/`DecEntry`
   untuk jam/menit/rate; `parse_angka` terima semua varian ("50.000", "Rp 50.000", "8,5").
3. Font hardcode "Segoe UI" rusak di Linux. Fix: `FONT/MONO` adaptif per OS.
4. Field invalid tidak merah (v3 cuma label). Fix: style `Invalid.TEntry` + pesan inline.
5. Label error pengaturan `s_err` tidak pernah di-pack (invisible). Fix: di-pack + dipakai.
6. Filter "minggu ini" pakai nomor minggu saja — bocor antar tahun (Des vs Jan).
   Fix: kunci `(iso_year, iso_week)` via `iso_week_key()`.
7. Window utama `geometry("1000x660")` tanpa posisi → OS taruh kiri-atas. Fix: center layar.
8. Backup DB copy saat koneksi terbuka (lock di Windows). Fix: tutup dulu, copy, popup tengah.
9. Laporan tidak bisa sortir, tanpa zebra, tanpa status. Fix: klik header sortir, zebra, footer.
10. Tidak ada konfirmasi keluar saat ada hitungan belum disimpan. Fix: flag `_unsaved` + confirm.

## 3. Scope v4
Masuk:
- 5 tab + menu File/Karyawan/Bantuan + banner + status bar + shortcut (F5, Ctrl+S, Ctrl+E).
- Popup custom tengah: info/ok/error/confirm/slip + dialog karyawan tengah + validasi inline.
- Entry pintar: MoneyEntry/IntEntry/DecEntry live format + kursor stabil + invalid merah.
- Hitung live tiap ketikan, tombol mati bila invalid, slip monospace rapi + salin/txt/laporan.
- Laporan: cari, filter minggu, sortir kolom, footer total, export CSV, hapus, backup DB.
- Stdlib only. DB + settings.json di folder EXE. run.bat/run.sh.
Tidak masuk (roadmap): login/multi-user, absensi harian, PPh21/BPJS, PDF, cloud sync,
  audit log user, periode gaji backdate, import Excel.

## 4. Aturan hitung (tetap)
jam_std = jam_per_hari × hari_per_minggu; normal_dibayar = min(jam_normal, jam_std);
lebih = max(0, jam_normal − jam_std); menit_jam = ceil(menit/pembulatan)×(pembulatan/60);
total_lembur = lebih + jam_lembur + menit_jam; pokok = normal_dibayar × upah;
lembur = total_lembur × upah × rate_lembur; libur = jam_libur × upah × rate_libur.

## 5. Kriteria terima v4
1. `py_compile` sukses; `tests_smoke.py` 100% lolos (hitung, menit, parse ID, ribu, week-key).
2. Tidak ada string `"+{px` / `"+px` di kode (sumber bug posisi).
3. Semua Toplevel (Popup/Slip/dialog) panggil `center_modal` + withdraw→deiconify.
4. Ketik `50000` di upah → tampil `50.000`; ketik `8,5` jam → valid 8.5.
5. Field salah → merah + pesan, tombol Simpan/Slip mati, tanpa crash.
6. Keluar dengan hitungan belum disimpan → konfirmasi muncul tengah.
7. Laporan: cari/filter/sortir benar; export CSV ada; backup DB ada.
8. EXE CI Windows jalan tanpa Python; README run.bat/run.sh akurat.

## 6. Cara jalan
Windows: PayrollPro.exe → double-click. Linux: ./PayrollPro. Source: python payroll_gui.py.
Data payroll.db + settings.json otomatis di folder yang sama. Backup via menu File.
