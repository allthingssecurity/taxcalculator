from fastapi import FastAPI, UploadFile, File, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Dict, Any
import io
import uuid
import time
from openpyxl import Workbook

from .parsing.reader import read_transactions
from .core.engine import process_transactions
from .reports.export import (
    dataframes_to_csv_bytes,
    dataframes_to_excel_bytes,
)


app = FastAPI(title="Equity CG Calculator", version="1.0.0")

templates = Jinja2Templates(directory="app/ui/templates")
app.mount("/static", StaticFiles(directory="app/ui/static"), name="static")


# In-memory result store keyed by token
RESULTS: Dict[str, Dict[str, Any]] = {}
RESULT_TTL_SECONDS = 60 * 30


def _cleanup_results() -> None:
    now = time.time()
    expired = [k for k, v in RESULTS.items() if now - v.get("ts", now) > RESULT_TTL_SECONDS]
    for k in expired:
        RESULTS.pop(k, None)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/process")
async def process(file: UploadFile = File(...)):
    try:
        content = await file.read()
        df, validations = read_transactions(io.BytesIO(content))
        if validations["errors"]:
            return JSONResponse({"ok": False, "validations": validations}, status_code=400)

        try:
            results = process_transactions(df)
        except ValueError as ve:
            return JSONResponse({"ok": False, "validations": {"errors": [str(ve)], "warnings": []}}, status_code=400)
        token = str(uuid.uuid4())
        RESULTS[token] = {"ts": time.time(), **results}
        _cleanup_results()
        return {"ok": True, "token": token, "validations": validations, **_summaries_for_ui(results)}
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


def _summaries_for_ui(results: Dict[str, Any]) -> Dict[str, Any]:
    # Convert DataFrames to records for quick rendering in UI
    rl = results["realized_lots"].to_dict(orient="records")
    ps = results["per_scrip_summary"].to_dict(orient="records")
    os = results["overall_summary"].to_dict(orient="records")
    op = results["open_positions"].to_dict(orient="records")
    return {
        "realized_lots": rl,
        "per_scrip_summary": ps,
        "overall_summary": os,
        "open_positions": op,
    }


def _get_result_token(token: str) -> Dict[str, Any]:
    data = RESULTS.get(token)
    if not data:
        raise HTTPException(status_code=404, detail="Token not found or expired")
    return data


@app.get("/download/{token}/csv")
def download_csv(token: str):
    res = _get_result_token(token)
    bio = io.BytesIO(dataframes_to_csv_bytes(res))
    headers = {"Content-Disposition": f"attachment; filename=reports_{token}.zip"}
    return StreamingResponse(bio, media_type="application/zip", headers=headers)


@app.get("/download/{token}/excel")
def download_excel(token: str):
    res = _get_result_token(token)
    bio = io.BytesIO(dataframes_to_excel_bytes(res))
    headers = {"Content-Disposition": f"attachment; filename=reports_{token}.xlsx"}
    return StreamingResponse(bio, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=headers)


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/sample/template.xlsx")
def sample_template():
    wb = Workbook()
    ws = wb.active
    ws.title = "Transactions"
    ws.append([
        "TradeDate",
        "Scrip",
        "Action",
        "Quantity",
        "Price",
        "Brokerage",
        "Charges",
        "STT",
        "Exchange",
        "ISIN",
        "Notes",
    ])
    # Sample rows
    ws.append(["2023-01-01", "TCS", "BUY", 100, 3000, 10, 5, 0, "NSE", "INE467B01029", "Initial buy"])
    ws.append(["2023-03-01", "TCS", "BUY", 50, 3200, 10, 5, 0, "NSE", "INE467B01029", "Additional buy"])
    ws.append(["2023-06-15", "TCS", "SELL", 80, 3300, 12, 6, 3, "NSE", "INE467B01029", "Partial sell"])
    ws.append(["2024-01-10", "TCS", "SELL", 30, 3400, 12, 6, 3, "NSE", "INE467B01029", "Another sell"])
    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    headers = {"Content-Disposition": "attachment; filename=sample_template.xlsx"}
    return StreamingResponse(bio, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=headers)
