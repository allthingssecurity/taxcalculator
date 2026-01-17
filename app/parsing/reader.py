from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple
import pandas as pd
import numpy as np

from .mapping import COLUMN_MAPPING, REQUIRED_FIELDS, OPTIONAL_FIELDS


@dataclass
class ValidationReport:
    errors: List[str]
    warnings: List[str]


def _resolve_columns(df: pd.DataFrame) -> Dict[str, str]:
    lower_cols = {c.lower().strip(): c for c in df.columns}
    resolved: Dict[str, str] = {}
    for canon, options in COLUMN_MAPPING.items():
        for opt in options:
            if opt in lower_cols:
                resolved[canon] = lower_cols[opt]
                break
    return resolved


def _coerce_types(df: pd.DataFrame, colmap: Dict[str, str], validations: ValidationReport) -> pd.DataFrame:
    # Dates
    if "trade_date" in colmap:
        df[colmap["trade_date"]] = pd.to_datetime(df[colmap["trade_date"]], errors="coerce").dt.date
    # Numerics
    for num in ["quantity", "price", "brokerage", "charges", "stt"]:
        if num in colmap:
            df[colmap[num]] = pd.to_numeric(df[colmap[num]], errors="coerce")
    return df


def _canonicalize(df: pd.DataFrame, colmap: Dict[str, str]) -> pd.DataFrame:
    out = pd.DataFrame()
    # Required
    out["trade_date"] = df[colmap["trade_date"]]
    out["scrip"] = df[colmap["scrip"]].astype(str).str.strip()
    out["action"] = df[colmap["action"]].astype(str).str.upper().str.strip()
    out["quantity"] = df[colmap["quantity"]]
    out["price"] = df[colmap["price"]]
    # Optional with defaults
    out["brokerage"] = df[colmap.get("brokerage", "brokerage_missing")] if "brokerage" in colmap else 0.0
    out["charges"] = df[colmap.get("charges", "charges_missing")] if "charges" in colmap else 0.0
    out["stt"] = df[colmap.get("stt", "stt_missing")] if "stt" in colmap else 0.0
    out["exchange"] = df[colmap.get("exchange", "exchange_missing")] if "exchange" in colmap else ""
    out["isin"] = df[colmap.get("isin", "isin_missing")] if "isin" in colmap else ""
    out["notes"] = df[colmap.get("notes", "notes_missing")] if "notes" in colmap else ""
    # Add row id for tracing
    out["source_row_id"] = np.arange(1, len(out) + 1)
    return out


def read_transactions(fobj: Any) -> Tuple[pd.DataFrame, Dict[str, List[str]]]:
    """Read Excel and return canonical DataFrame + validation report dict."""
    validations = ValidationReport(errors=[], warnings=[])

    xls = pd.ExcelFile(fobj)
    sheet = "Transactions" if "Transactions" in xls.sheet_names else xls.sheet_names[0]
    df = xls.parse(sheet)
    if df.empty:
        validations.errors.append("Uploaded sheet is empty")
        return df, validations.__dict__

    colmap = _resolve_columns(df)

    # Ensure required fields present
    for req in REQUIRED_FIELDS:
        if req not in colmap:
            validations.errors.append(f"Missing required column: {req}")

    if validations.errors:
        return df, validations.__dict__

    df = _coerce_types(df, colmap, validations)

    # Basic validations
    if df[colmap["action"]].str.upper().isin(["BUY", "SELL"]).all() is False:
        validations.errors.append("Unknown action values present; allowed BUY/SELL")

    if df[colmap["trade_date"]].isna().any():
        validations.errors.append("Some trade dates are invalid or missing")

    if df[colmap["quantity"]].le(0).any():
        validations.errors.append("Quantities must be positive")

    if df[colmap["price"]].lt(0).any():
        validations.errors.append("Prices must be non-negative")

    if validations.errors:
        return df, validations.__dict__

    canon = _canonicalize(df, colmap)

    # Warn on fractional quantity
    if (canon["quantity"] % 1 != 0).any():
        validations.warnings.append("Some quantities are fractional; treating as-is")

    return canon, validations.__dict__

