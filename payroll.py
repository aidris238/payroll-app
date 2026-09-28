#!/usr/bin/env python3
"""
Aplikasi Penggajian Karyawan - Mingguan
- Input: upah per jam, jam kerja normal, jam lembur, menit tambahan
- Output: total gaji mingguan dengan rincian
"""

import sys
import json
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class PayrollConfig:
    """Konfigurasi perhitungan gaji"""
    upah_per_jam: float
    jam_kerja_normal_per_hari: float = 8.0
    hari_kerja_per_minggu: int = 6
    jam_lembur_mulai: float = 8.0  # jam ke-9 mulai lembur
    rate_lembur: float = 1.5
    rate_lembur_hari_libur: float = 2.0
    pembulatan_menit: int = 15  # menit ke atas dibulatkan jadi 1 jam


@dataclass
class WorkHours:
    """Jam kerja karyawan per minggu"""
    jam_normal: float = 0.0
    jam_lembur: float = 0.0
    jam_lembur_libur: float = 0.0
    menit_tambahan: int = 0


@dataclass
class PayrollResult:
    """Hasil perhitungan gaji"""
    gaji_pokok: float
    gaji_lembur: float
    gaji_lembur_libur: float
    total_gaji: float
    rincian: dict


def bulatkan_menit(menit: int, pembulatan: int = 15) -> float:
    """Bulatkan menit ke atas ke kelipatan pembulatan (dalam jam)"""
    if menit <= 0:
        return 0.0
    jam_tambahan = (menit + pembulatan - 1) // pembulatan
    return jam_tambahan * (pembulatan / 60)


def hitung_gaji(config: PayrollConfig, hours: WorkHours) -> PayrollResult:
    """Hitung total gaji mingguan"""
    # Jam kerja normal per minggu
    jam_normal_minggu = config.jam_kerja_normal_per_hari * config.hari_kerja_per_minggu
    
    # Hitung jam normal (maksimal jam_normal_minggu)
    jam_normal_dibayar = min(hours.jam_normal, jam_normal_minggu)
    jam_lebih_dari_normal = max(0, hours.jam_normal - jam_normal_minggu)
    
    # Jam lembur = jam lebih dari normal + jam_lembur input + jam dari menit tambahan
    menit_jam = bulatkan_menit(hours.menit_tambahan, config.pembulatan_menit)
    total_jam_lembur = jam_lebih_dari_normal + hours.jam_lembur + menit_jam
    
    # Gaji pokok
    gaji_pokok = jam_normal_dibayar * config.upah_per_jam
    
    # Gaji lembur biasa
    gaji_lembur = total_jam_lembur * config.upah_per_jam * config.rate_lembur
    
    # Gaji lembur hari libur
    gaji_lembur_libur = hours.jam_lembur_libur * config.upah_per_jam * config.rate_lembur_hari_libur
    
    total = gaji_pokok + gaji_lembur + gaji_lembur_libur
    
    rincian = {
        "upah_per_jam": config.upah_per_jam,
        "jam_kerja_normal_per_hari": config.jam_kerja_normal_per_hari,
        "hari_kerja_per_minggu": config.hari_kerja_per_minggu,
        "jam_normal_dibayar": jam_normal_dibayar,
        "jam_lembur_total": total_jam_lembur,
        "jam_lembur_libur": hours.jam_lembur_libur,
        "menit_tambahan": hours.menit_tambahan,
        "menit_dibulatkan_jam": menit_jam,
        "rate_lembur": config.rate_lembur,
        "rate_lembur_libur": config.rate_lembur_hari_libur,
        "pembulatan_menit": config.pembulatan_menit,
    }
    
    return PayrollResult(
        gaji_pokok=gaji_pokok,
        gaji_lembur=gaji_lembur,
        gaji_lembur_libur=gaji_lembur_libur,
        total_gaji=total,
        rincian=rincian
    )


def format_rupiah(amount: float) -> str:
    """Format angka jadi Rupiah"""
    return f"Rp {amount:,.0f}".replace(",", ".")


def input_float(prompt: str, default: float = 0.0) -> float:
    """Input float dengan default"""
    val = input(f"{prompt} [{default}]: ").strip()
    return float(val) if val else default


def input_int(prompt: str, default: int = 0) -> int:
    """Input int dengan default"""
    val = input(f"{prompt} [{default}]: ").strip()
    return int(val) if val else default


def main():
    print("=" * 50)
    print("  APLIKASI PENGGAJIAN KARYAWAN (MINGGUAN)")
    print("=" * 50)
    print()
    
    # Konfigurasi
    print("--- KONFIGURASI UPAH ---")
    upah_per_jam = input_float("Upah per jam", 50000)
    jam_kerja_normal = input_float("Jam kerja normal per hari", 8.0)
    hari_kerja = input_int("Hari kerja per minggu", 6)
    pembulatan = input_int("Pembulatan menit ke atas (menit)", 15)
    
    config = PayrollConfig(
        upah_per_jam=upah_per_jam,
        jam_kerja_normal_per_hari=jam_kerja_normal,
        hari_kerja_per_minggu=hari_kerja,
        pembulatan_menit=pembulatan
    )
    
    print()
    print("--- JAM KERJA KARYAWAN MINGGU INI ---")
    jam_normal = input_float("Jam kerja normal (total mingguan)", 48.0)
    jam_lembur = input_float("Jam lembur (di luar jam normal)", 0.0)
    jam_lembur_libur = input_float("Jam lembur hari libur", 0.0)
    menit_tambahan = input_int("Menit tambahan (akan dibulatkan ke atas)", 0)
    
    hours = WorkHours(
        jam_normal=jam_normal,
        jam_lembur=jam_lembur,
        jam_lembur_libur=jam_lembur_libur,
        menit_tambahan=menit_tambahan
    )
    
    # Hitung
    result = hitung_gaji(config, hours)
    
    # Output
    print()
    print("=" * 50)
    print("  HASIL PERHITUNGAN GAJI MINGGUAN")
    print("=" * 50)
    print(f"Gaji Pokok        : {format_rupiah(result.gaji_pokok)}")
    print(f"Gaji Lembur       : {format_rupiah(result.gaji_lembur)}")
    print(f"Gaji Lembur Libur : {format_rupiah(result.gaji_lembur_libur)}")
    print("-" * 50)
    print(f"TOTAL GAJI        : {format_rupiah(result.total_gaji)}")
    print("=" * 50)
    
    print()
    print("--- RINCIAN ---")
    for k, v in result.rincian.items():
        print(f"  {k}: {v}")
    
    # Simpan ke file JSON
    output = {
        "config": asdict(config),
        "hours": asdict(hours),
        "result": asdict(result)
    }
    with open("payroll_result.json", "w") as f:
        json.dump(output, f, indent=2, default=str)
    print("\n[✓] Hasil disimpan ke payroll_result.json")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDibatalkan.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)