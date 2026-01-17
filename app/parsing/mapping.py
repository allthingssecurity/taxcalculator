from typing import Dict, List

# Canonical fields we expect internally
REQUIRED_FIELDS: List[str] = [
    "trade_date",
    "scrip",
    "action",
    "quantity",
    "price",
]

OPTIONAL_FIELDS: List[str] = [
    "brokerage",
    "charges",
    "stt",
    "exchange",
    "isin",
    "notes",
]


# Map canonical field -> list of possible column names in Excel
COLUMN_MAPPING: Dict[str, List[str]] = {
    "trade_date": ["tradedate", "trade_date", "date", "txn_date"],
    "scrip": ["scrip", "symbol", "stock", "name"],
    "action": ["action", "type", "side"],
    "quantity": ["quantity", "qty", "shares"],
    "price": ["price", "rate", "unitprice"],
    "brokerage": ["brokerage", "broker", "brokerage_amt"],
    "charges": ["charges", "fees", "other_charges"],
    "stt": ["stt", "sebi_stt", "stt_amt"],
    "exchange": ["exchange", "exch"],
    "isin": ["isin"],
    "notes": ["notes", "remark", "remarks"],
}

