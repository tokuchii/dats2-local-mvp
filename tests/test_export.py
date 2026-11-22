from __future__ import annotations

import io
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

os.environ.setdefault("REVIEWER_TOKEN", "change-this-local-reviewer-token")

from openpyxl import load_workbook

from app.main import app
from app.db import count_systems, get_summary, init_db


def test_filtered_export_preview_and_downloads():
    init_db()
    expected = count_systems(search="DigiSaka")
    assert expected >= 1

    with TestClient(app) as client:
        preview = client.get("/export/preview", params={"search": "DigiSaka"})
        assert preview.status_code == 200
        assert "D2-099" in preview.text
        assert "DigiSaka" in preview.text
        assert "Download XLSX" in preview.text
        assert "Download CSV" in preview.text
        assert "/export/current.xlsx?search=DigiSaka" in preview.text

        xlsx = client.get("/export/current.xlsx", params={"search": "DigiSaka"})
        assert xlsx.status_code == 200
        workbook = load_workbook(io.BytesIO(xlsx.content))
        assert workbook.sheetnames == ["Systems", "Export Info"]
        sheet = workbook["Systems"]
        assert sheet.max_row == expected + 1
        assert sheet["A1"].value == "DATS2_ID"
        assert sheet.freeze_panes == "A2"
        assert sheet.auto_filter.ref
        assert str(sheet["A1"].fill.fgColor.rgb).upper().endswith("0B2E59")
        ids = [cell.value for cell in sheet["A"][1:]]
        assert "D2-099" in ids
        assert workbook["Export Info"]["B3"].value == expected

        csv_response = client.get("/export/current.csv", params={"search": "DigiSaka"})
        assert csv_response.status_code == 200
        csv_text = csv_response.content.decode("utf-8-sig")
        csv_lines = [line for line in csv_text.splitlines() if line.strip()]
        assert len(csv_lines) == expected + 1
        assert "D2-099" in csv_text

        all_preview = client.get("/export/preview")
        assert all_preview.status_code == 200
        assert str(get_summary()["systems"]) in all_preview.text

        modal = client.get("/export/modal", params={"search": "DigiSaka"})
        assert modal.status_code == 200
        assert "D2-099" in modal.text
        assert "Scroll sideways to view all 29 columns" in modal.text
        assert "export-modal-title" in modal.text
        assert "data-export-print" in modal.text
        assert "/export/print?search=DigiSaka" in modal.text
        assert "auto=1" in modal.text

        print_page = client.get("/export/print", params={"search": "DigiSaka"})
        assert print_page.status_code == 200
        assert "D2-099" in print_page.text
        assert "print-page" in print_page.text
        assert "window.print" in print_page.text
        assert "1 matching record" in print_page.text

        systems = client.get("/systems", params={"search": "DigiSaka"})
        assert systems.status_code == 200
        assert 'id="export-modal"' in systems.text
        assert "data-export-modal" in systems.text
        assert "/export/modal?search=DigiSaka" in systems.text

        modal_all = client.get("/export/modal")
        all_count = get_summary()["systems"]
        assert modal_all.status_code == 200
        assert f"Showing the first {min(all_count, 100)} of {all_count} matching records" in modal_all.text
