"""Excel import validation and security controls."""
from __future__ import annotations

import io

import pytest
from openpyxl import Workbook, load_workbook

from app.core.security import RateLimiter, UnsafeURLError, validate_public_url, validate_xlsx_upload
from app.services.ingestion.excel_parser import WorkbookError, parse_workbook


def test_parses_actual_meridian_layout(sample_bytes):
    r = parse_workbook(sample_bytes)
    assert r.valid and r.sheet_name == "Vendor Inventory" and r.header_row == 3
    assert [v.fields["vendor_ref"] for v in r.assessable] == ["V-001", "V-002", "V-003", "V-004", "V-005", "V-006"]
    assert r.report()["example_rows"] == ["V-000"]
    assert not r.missing_input_columns and not r.missing_output_columns     # incl. 'Assessedd By / Date' typo
    assert r.assessable[1].fields["operational_dependency"] == "Critical"


def _mutate(sample_bytes, fn) -> bytes:
    wb = load_workbook(io.BytesIO(sample_bytes))
    fn(wb["Vendor Inventory"])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_missing_required_column_is_an_error(sample_bytes):
    data = _mutate(sample_bytes, lambda ws: ws.cell(3, 10, "Something else"))   # Data Classification header
    r = parse_workbook(data)
    assert not r.valid and any("data_classification" in e for e in r.errors)


def test_duplicate_vendor_ids_detected(sample_bytes):
    data = _mutate(sample_bytes, lambda ws: ws.cell(6, 2, "V-001"))
    r = parse_workbook(data)
    assert "V-001" in r.duplicate_vendor_ids and not r.valid


def test_reordered_columns_still_map(sample_bytes):
    def swap(ws):
        for row in range(3, ws.max_row + 1):
            a, b = ws.cell(row, 3).value, ws.cell(row, 4).value
            ws.cell(row, 3, b)
            ws.cell(row, 4, a)
    r = parse_workbook(_mutate(sample_bytes, swap))
    assert r.valid and r.assessable[0].fields["name"] == "AutomWorx"


def test_workbook_without_header_rejected():
    wb = Workbook()
    wb.active["A1"] = "hello"
    buf = io.BytesIO()
    wb.save(buf)
    with pytest.raises(WorkbookError):
        parse_workbook(buf.getvalue())


def test_upload_validation():
    with pytest.raises(ValueError):
        validate_xlsx_upload("vendors.csv", b"PK\x03\x04data", 10)
    with pytest.raises(ValueError):
        validate_xlsx_upload("vendors.xlsx", b"not a zip", 10)
    with pytest.raises(ValueError):
        validate_xlsx_upload("vendors.xlsx", b"PK\x03\x04" + b"0" * (2 * 1024 * 1024), 1)
    validate_xlsx_upload("vendors.xlsx", b"PK\x03\x04data", 10)


@pytest.mark.parametrize("url", [
    "http://localhost/admin", "http://127.0.0.1:8000/", "http://169.254.169.254/latest/meta-data/",
    "http://10.0.0.5/", "http://[::1]/", "file:///etc/passwd", "ftp://example.com/x",
    "http://user:pw@example.com/", "http://example.com:6379/", "http://metadata.google.internal/",
    "http://intranet/", "http://db.internal/",
])
def test_ssrf_guard_blocks_internal_targets(url):
    with pytest.raises(UnsafeURLError):
        validate_public_url(url, resolve=False)


def test_ssrf_guard_allows_public_literal_ip():
    assert validate_public_url("https://93.184.216.34/", resolve=False)


def test_rate_limiter():
    rl = RateLimiter(2)
    assert rl.allow("a") and rl.allow("a") and not rl.allow("a") and rl.allow("b")
