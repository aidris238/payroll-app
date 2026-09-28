#!/usr/bin/env python3
"""
Aplikasi Penggajian Karyawan - Mingguan
Modern CLI dengan Rich: tabel warna, panel, progress, validasi input
"""

import sys
import json
from dataclasses import dataclass, asdict
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, FloatPrompt, IntPrompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text
from rich.align import Align
from rich.rule import Rule
from rich.layout import Layout
from rich.live import Live
from rich import box
from rich.columns import Columns

console = Console()


@dataclass
class PayrollConfig:
    """Konfigurasi perhitungan gaji"""
    upah_per_jam: float
    jam_kerja_normal_per_hari: float = 8.0
    hari_kerja_per_minggu: int = 6
    jam_lembur_mulai: float = 8.0
    rate_lembur: float = 1.5
    rate_lembur_hari_libur: float = 2.0
    pembulatan_menit: int = 15


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
    jam_normal_minggu = config.jam_kerja_normal_per_hari * config.hari_kerja_per_minggu
    
    jam_normal_dibayar = min(hours.jam_normal, jam_normal_minggu)
    jam_lebih_dari_normal = max(0, hours.jam_normal - jam_normal_minggu)
    
    menit_jam = bulatkan_menit(hours.menit_tambahan, config.pembulatan_menit)
    total_jam_lembur = jam_lebih_dari_normal + hours.jam_lembur + menit_jam
    
    gaji_pokok = jam_normal_dibayar * config.upah_per_jam
    gaji_lembur = total_jam_lembur * config.upah_per_jam * config.rate_lembur
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


def print_header():
    """Print header aplikasi"""
    title = Text("APLIKASI PENGGAJIAN KARYAWAN", style="bold white on blue")
    subtitle = Text("Perhitungan Mingguan • Lembur & Pembulatan Menit", style="italic cyan")
    
    console.print()
    console.print(Align.center(Panel(title, subtitle=subtitle, border_style="blue", box=box.DOUBLE)))
    console.print()


def print_section(title: str, style: str = "cyan"):
    """Print section divider"""
    console.print(Rule(f"[{style}]{title}[/{style}]", style=style))


def get_config() -> PayrollConfig:
    """Input konfigurasi upah dengan validasi"""
    print_section("⚙️  KONFIGURASI UPAH")
    
    upah = FloatPrompt.ask(
        "[bold cyan]Upah per jam[/bold cyan]",
        default=50000.0,
        show_default=True
    )
    
    jam_hari = FloatPrompt.ask(
        "[bold cyan]Jam kerja normal per hari[/bold cyan]",
        default=8.0,
        show_default=True
    )
    
    hari = IntPrompt.ask(
        "[bold cyan]Hari kerja per minggu[/bold cyan]",
        default=6,
        show_default=True
    )
    
    pembulatan = IntPrompt.ask(
        "[bold cyan]Pembulatan menit ke atas (menit)[/bold cyan]",
        default=15,
        show_default=True
    )
    
    # Advanced settings
    if Confirm.ask("[dim]Tampilkan pengaturan lanjutan?[/dim]", default=False):
        rate_lembur = FloatPrompt.ask(
            "[bold cyan]Rate lembur (x)[/bold cyan]",
            default=1.5,
            show_default=True
        )
        rate_libur = FloatPrompt.ask(
            "[bold cyan]Rate lembur hari libur (x)[/bold cyan]",
            default=2.0,
            show_default=True
        )
    else:
        rate_lembur = 1.5
        rate_libur = 2.0
    
    return PayrollConfig(
        upah_per_jam=upah,
        jam_kerja_normal_per_hari=jam_hari,
        hari_kerja_per_minggu=hari,
        pembulatan_menit=pembulatan,
        rate_lembur=rate_lembur,
        rate_lembur_hari_libur=rate_libur
    )


def get_work_hours(config: PayrollConfig) -> WorkHours:
    """Input jam kerja karyawan"""
    print_section("📋 JAM KERJA MINGGU INI")
    
    jam_normal_minggu = config.jam_kerja_normal_per_hari * config.hari_kerja_per_minggu
    console.print(f"[dim]Jam normal standar per minggu: {jam_normal_minggu:.1f} jam ({config.hari_kerja_per_minggu} hari × {config.jam_kerja_normal_per_hari:.1f} jam)[/dim]")
    
    jam_normal = FloatPrompt.ask(
        "[bold cyan]Jam kerja normal (total mingguan)[/bold cyan]",
        default=jam_normal_minggu,
        show_default=True
    )
    
    jam_lembur = FloatPrompt.ask(
        "[bold cyan]Jam lembur (di luar jam normal)[/bold cyan]",
        default=0.0,
        show_default=True
    )
    
    jam_lembur_libur = FloatPrompt.ask(
        "[bold cyan]Jam lembur hari libur[/bold cyan]",
        default=0.0,
        show_default=True
    )
    
    menit_tambahan = IntPrompt.ask(
        "[bold cyan]Menit tambahan (akan dibulatkan ke atas)[/bold cyan]",
        default=0,
        show_default=True
    )
    
    return WorkHours(
        jam_normal=jam_normal,
        jam_lembur=jam_lembur,
        jam_lembur_libur=jam_lembur_libur,
        menit_tambahan=menit_tambahan
    )


def print_result(config: PayrollConfig, hours: WorkHours, result: PayrollResult):
    """Tampilkan hasil dengan tabel yang rapi"""
    print_section("💰 HASIL PERHITUNGAN")
    
    # Tabel utama
    table = Table(box=box.ROUNDED, show_header=False, padding=(0, 2))
    table.add_column("Keterangan", style="cyan", width=25)
    table.add_column("Jumlah", style="bold green", justify="right", width=20)
    
    table.add_row("Gaji Pokok", format_rupiah(result.gaji_pokok))
    table.add_row("Gaji Lembur", format_rupiah(result.gaji_lembur))
    table.add_row("Gaji Lembur Libur", format_rupiah(result.gaji_lembur_libur))
    table.add_section()
    table.add_row("TOTAL GAJI", format_rupiah(result.total_gaji))
    
    console.print(Panel(table, title="[bold green]Rincian Gaji Mingguan[/bold green]", border_style="green"))
    
    # Tabel rincian perhitungan
    detail_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    detail_table.add_column("Item", style="dim cyan")
    detail_table.add_column("Nilai", style="white")
    
    r = result.rincian
    detail_table.add_row("Upah per jam", format_rupiah(r["upah_per_jam"]))
    detail_table.add_row("Jam normal dibayar", f"{r['jam_normal_dibayar']:.1f} jam")
    detail_table.add_row("Jam lembur total", f"{r['jam_lembur_total']:.2f} jam")
    detail_table.add_row("  ├─ Dari jam lebih", f"{max(0, hours.jam_normal - config.jam_kerja_normal_per_hari * config.hari_kerja_per_minggu):.1f} jam")
    detail_table.add_row("  ├─ Input lembur", f"{hours.jam_lembur:.1f} jam")
    detail_table.add_row("  └─ Dari menit ({} menit → {:.2f} jam)".format(r['menit_tambahan'], r['menit_dibulatkan_jam']), "")
    detail_table.add_row("Jam lembur libur", f"{r['jam_lembur_libur']:.1f} jam")
    detail_table.add_row("Rate lembur", f"{r['rate_lembur']}x")
    detail_table.add_row("Rate lembur libur", f"{r['rate_lembur_libur']}x")
    detail_table.add_row("Pembulatan menit", f"{r['pembulatan_menit']} menit")
    
    console.print(Panel(detail_table, title="[bold cyan]Detail Perhitungan[/bold cyan]", border_style="cyan"))


def save_result(config: PayrollConfig, hours: WorkHours, result: PayrollResult):
    """Simpan hasil ke JSON"""
    output = {
        "config": asdict(config),
        "hours": asdict(hours),
        "result": asdict(result)
    }
    with open("payroll_result.json", "w") as f:
        json.dump(output, f, indent=2, default=str)
    
    console.print("\n[green]✓[/green] Hasil disimpan ke [bold]payroll_result.json[/bold]")


def show_summary(config: PayrollConfig, hours: WorkHours, result: PayrollResult):
    """Ringkasan cepat di bawah"""
    console.print()
    total_jam = hours.jam_normal + hours.jam_lembur + hours.jam_lembur_libur
    avg_per_jam = result.total_gaji / max(1, total_jam)
    
    summary = Columns([
        Panel(
            f"[bold]{format_rupiah(result.total_gaji)}[/bold]\n[dim]Total Gaji[/dim]",
            title="💵 Total",
            border_style="green",
            width=30
        ),
        Panel(
            f"[bold]{total_jam:.1f} jam[/bold]\n[dim]Total Jam Kerja[/dim]",
            title="⏱️ Jam",
            border_style="blue",
            width=30
        ),
        Panel(
            f"[bold]{format_rupiah(avg_per_jam)}/jam[/bold]\n[dim]Rata-rata/jam[/dim]",
            title="📊 Avg",
            border_style="yellow",
            width=30
        ),
    ], equal=True, expand=True)
    console.print(summary)


def main():
    console.clear()
    print_header()
    
    try:
        # Input
        config = get_config()
        hours = get_work_hours(config)
        
        # Loading animation
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            task = progress.add_task("[cyan]Menghitung gaji...", total=None)
            import time
            time.sleep(0.5)
            result = hitung_gaji(config, hours)
        
        # Output
        print_result(config, hours, result)
        show_summary(config, hours, result)
        save_result(config, hours, result)
        
        # Opsi simpan/cetak
        console.print()
        if Confirm.ask("[bold]Hitung lagi untuk karyawan lain?[/bold]", default=False):
            console.print()
            main()  # recursive untuk karyawan berikutnya
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Dibatalkan oleh user.[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()