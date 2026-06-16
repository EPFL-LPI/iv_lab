"""J-V PDF report tests (headless, all in tmp_path)."""

from pathlib import Path

from iv_lab.data import FileWriter, IVResults, SystemContext
from iv_lab.data.pdf_report import generate_jv_results_pdf, wrap_data_file_name


def make_context(tmp_path: Path, **overrides) -> SystemContext:
    data = dict(
        base_path=str(tmp_path / "data_root"),
        sd_path="",
        system_name="IVLab",
        smu_brand="Keithley",
        smu_model="2602",
        lamp_display_name="Sinus70 (Wavelabs)",
        use_reference_diode=True,
        full_sun_reference_current=0.004,
        calibration_datetime="Wed Jun  8 16:07:18 2022",
    )
    data.update(overrides)
    return SystemContext(**data)


def iv_result() -> IVResults:
    return IVResults(
        start_time="20260612_140000",
        cell_name="cellA",
        active_area=0.16,
        light_int=100.0,
        light_int_meas=99.5,
        Nwire="2 wire",
        start_V=0.0,
        stop_V=0.6,
        dV=0.05,
        sweep_rate=0.05,
        Imax=0.01,
        Dwell=5.0,
        voltage=[0.0, 0.3, 0.6],
        current=[-0.004, -0.0035, 0.002],
        Voc=0.55,
        Jsc=-25.0,
        Vmpp=0.45,
        Jmpp=-22.0,
        Pmpp=9.9,
        PCE=9.9,
        FF=0.72,
    )


def test_pdf_is_generated(tmp_path: Path) -> None:
    pdf_path = tmp_path / "report.pdf"

    generate_jv_results_pdf(
        iv_result(), "felix", make_context(tmp_path), "data.csv", pdf_path
    )

    assert pdf_path.exists()
    assert pdf_path.read_bytes()[:5] == b"%PDF-"
    assert pdf_path.stat().st_size > 1000


def test_pdf_with_logo(tmp_path: Path) -> None:
    # any readable image works; a tiny PNG
    import struct
    import zlib

    def png_bytes() -> bytes:
        def chunk(tag, payload):
            data = tag + payload
            return (
                struct.pack(">I", len(payload))
                + data
                + struct.pack(">I", zlib.crc32(data))
            )

        header = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
        raw = zlib.compress(b"\x00\xff\x00\x00")
        return (
            b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", header)
            + chunk(b"IDAT", raw)
            + chunk(b"IEND", b"")
        )

    logo_path = tmp_path / "logo.png"
    logo_path.write_bytes(png_bytes())
    pdf_path = tmp_path / "report.pdf"

    generate_jv_results_pdf(
        iv_result(),
        "felix",
        make_context(tmp_path, logo_path=str(logo_path)),
        "data.csv",
        pdf_path,
    )

    assert pdf_path.exists()


def test_missing_logo_is_skipped(tmp_path: Path) -> None:
    pdf_path = tmp_path / "report.pdf"
    context = make_context(tmp_path, logo_path=str(tmp_path / "missing.png"))

    generate_jv_results_pdf(iv_result(), "felix", context, "data.csv", pdf_path)

    assert pdf_path.exists()


def test_file_writer_generates_pdf_for_jv(tmp_path: Path) -> None:
    writer = FileWriter(make_context(tmp_path))  # generate_pdf defaults True

    csv_path, pdf_path = writer.save(iv_result(), "felix")

    assert pdf_path is not None
    assert pdf_path.exists()
    assert pdf_path.name == "cellA_JV_20260612_140000.pdf"
    assert pdf_path.parent == csv_path.parent


def test_wrap_data_file_name_legacy_quirk() -> None:
    # short names: single row
    assert wrap_data_file_name("short.csv") == [("Data File Name", "short.csv", "")]

    # long names: 30-character chunks despite the 35-character threshold
    name = "a" * 80
    rows = wrap_data_file_name(name)
    assert rows[0] == ("Data File Name", "a" * 30, "")
    assert rows[1] == ("", "a" * 30, "")
    assert rows[2] == ("", "a" * 20, "")
    assert "".join(row[1] for row in rows) == name
