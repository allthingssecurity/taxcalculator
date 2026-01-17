Equity Capital Gains Calculator (India) — v1
================================================

A FastAPI web app that computes STCG/LTCG for Indian equity share transactions from an uploaded Excel. It performs FIFO matching, generates realized lots, per-scrip and overall summaries, and open positions, with CSV/Excel downloads.

Stack
-----
- Backend: FastAPI (Python)
- Parsing: pandas + openpyxl
- UI: Jinja2 templates + vanilla JS
- Packaging: requirements.txt
- Tests: pytest

Run Locally
-----------
1. Python 3.11+ recommended.
2. Install dependencies:
   - `python3 -m venv .venv && source .venv/bin/activate`
   - `pip install -r requirements.txt`
3. Start server:
   - `uvicorn app.main:app --reload`
4. Open `http://127.0.0.1:8000` and upload an Excel.

Excel Input (v1)
----------------
- Sheet: `Transactions` (or first sheet if missing).
- Columns (case-insensitive): `TradeDate`, `Scrip`, `Action (BUY/SELL)`, `Quantity`, `Price`, optional: `Brokerage`, `Charges`, `STT`, `Exchange`, `ISIN`, `Notes`.
- For BUY: cost basis = qty*price + brokerage + charges.
- For SELL: proceeds net = qty*price - brokerage - charges - STT (STT assumed on sell).
- Quantities should be positive; decimals allowed but warned.

Download a sample template from `/sample/template.xlsx` or via the UI link.

Outputs
-------
- Realized Lots Report: per matched lot (FIFO), with Buy/Sell dates, Qty, HoldingDays, Term, costs, proceeds, gain, and source row IDs.
- Per Scrip Summary: STCG, LTCG, net gain, buy cost, sell proceeds, #sells, #matched lots.
- Overall Summary: totals across scrips.
- Open Positions: remaining buy lots with quantity, cost, and age.
- Downloads: CSV (zip) and Excel.

API
---
- `POST /api/process` form-data with `file` (.xlsx) returns JSON with summaries and a token for downloads.
- `GET /download/{token}/csv` and `/download/{token}/excel` for downloads.

Architecture
------------
- `app/parsing/`: Excel reading and canonicalization with a mapping layer for column names. Designed to adapt to future formats.
- `app/core/`: FIFO matching engine and computation of realized lots and open positions.
- `app/reports/`: Export helpers to CSV/Excel.
- `app/ui/`: Minimal SPA-like HTML+JS to upload, render results, and download.

Assumptions
-----------
- Equity shares only; 365-day threshold for ST/LT.
- FIFO matching per scrip.
- INR only.
- No corporate actions or indexation in v1.
- This is an aid for tracking; not legal/tax advice.

Tests
-----
Run `pytest`.

Covers:
- Partial sells across multiple buys
- Sells exceeding available buys (error)
- Exact 365-day boundary classification

Known Limitations
-----------------
- No database; results held in memory for 30 minutes.
- No handling of intraday, corporate actions, splits/bonuses.
- Single currency.

Future Format Changes
---------------------
The mapping layer (`app/parsing/mapping.py`) maps canonical fields to possible column names. Missing required fields are reported clearly. A transform step can be added in `reader.py` to support new formats (e.g., multiple sheets, combined columns).

