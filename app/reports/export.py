from __future__ import annotations

import io
import zipfile
from typing import Dict, Any
import pandas as pd


def dataframes_to_csv_bytes(results: Dict[str, Any]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name in [
            ("realized_lots.csv", results["realized_lots"]),
            ("per_scrip_summary.csv", results["per_scrip_summary"]),
            ("overall_summary.csv", results["overall_summary"]),
            ("open_positions.csv", results["open_positions"]),
        ]:
            zf.writestr(name[0], name[1].to_csv(index=False))
    return buf.getvalue()


def dataframes_to_excel_bytes(results: Dict[str, Any]) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        results["realized_lots"].to_excel(writer, index=False, sheet_name="RealizedLots")
        results["per_scrip_summary"].to_excel(writer, index=False, sheet_name="PerScripSummary")
        results["overall_summary"].to_excel(writer, index=False, sheet_name="OverallSummary")
        results["open_positions"].to_excel(writer, index=False, sheet_name="OpenPositions")
    return buf.getvalue()

