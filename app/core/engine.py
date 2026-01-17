from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Any, Tuple
import pandas as pd
from datetime import date


@dataclass
class BuyLot:
    buy_date: date
    qty_remaining: float
    unit_cost: float  # includes buy-side costs per unit
    source_buy_row_id: int


def _prepare_rows(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    buys = df[df["action"] == "BUY"].copy()
    sells = df[df["action"] == "SELL"].copy()
    # embed buy costs into unit cost
    buys["unit_cost"] = (buys["price"] * buys["quantity"] + buys["brokerage"].fillna(0) + buys["charges"].fillna(0)) / buys["quantity"]
    # sell costs total for each sell row
    sells["sell_gross"] = sells["price"] * sells["quantity"]
    sells["sell_costs_total"] = sells["brokerage"].fillna(0) + sells["charges"].fillna(0) + sells["stt"].fillna(0)
    sells["sell_net"] = sells["sell_gross"] - sells["sell_costs_total"]
    return buys, sells


def _fifo_match_for_scrip(buys: pd.DataFrame, sells: pd.DataFrame, scrip: str) -> Tuple[List[Dict[str, Any]], List[BuyLot]]:
    lots: List[BuyLot] = []
    realized: List[Dict[str, Any]] = []

    # Initialize lots FIFO
    scrip_buys = buys.sort_values(["trade_date", "source_row_id"])  # deterministic
    for _, r in scrip_buys.iterrows():
        lots.append(
            BuyLot(
                buy_date=r["trade_date"],
                qty_remaining=float(r["quantity"]),
                unit_cost=float(r["unit_cost"]),
                source_buy_row_id=int(r["source_row_id"]),
            )
        )

    scrip_sells = sells.sort_values(["trade_date", "source_row_id"])  # deterministic
    for _, sr in scrip_sells.iterrows():
        sell_qty = float(sr["quantity"])
        if sum(l.qty_remaining for l in lots) + 1e-9 < sell_qty:
            raise ValueError(f"Sell exceeds available buys for {scrip} on row {int(sr['source_row_id'])}")

        remaining_to_sell = sell_qty
        sell_costs_total = float(sr["sell_costs_total"])
        sell_gross = float(sr["sell_gross"])
        sell_date = sr["trade_date"]
        sell_row_id = int(sr["source_row_id"])

        while remaining_to_sell > 1e-12:
            lot = lots[0]
            take_qty = min(lot.qty_remaining, remaining_to_sell)
            # Pro-rata allocation of sell costs and gross
            fraction = take_qty / sell_qty
            proceeds_gross = sell_gross * fraction
            costs_alloc = sell_costs_total * fraction
            proceeds_net = proceeds_gross - costs_alloc
            buy_cost_total = take_qty * lot.unit_cost
            gain = proceeds_net - buy_cost_total
            holding_days = (sell_date - lot.buy_date).days
            term = "ST" if holding_days < 365 else "LT"

            realized.append(
                {
                    "Scrip": scrip,
                    "BuyDate": lot.buy_date,
                    "SellDate": sell_date,
                    "Qty": take_qty,
                    "HoldingDays": holding_days,
                    "Term": term,
                    "BuyUnitCost": lot.unit_cost,
                    "BuyCostTotal": buy_cost_total,
                    "SellUnitPrice": float(sr["price"]),
                    "SellProceedsGross": proceeds_gross,
                    "SellCostsAllocated": costs_alloc,
                    "SellProceedsNet": proceeds_net,
                    "Gain": gain,
                    "BuyRef": lot.source_buy_row_id,
                    "SellRef": sell_row_id,
                }
            )

            lot.qty_remaining -= take_qty
            remaining_to_sell -= take_qty
            if lot.qty_remaining <= 1e-12:
                lots.pop(0)

    return realized, lots


def process_transactions(canon_df: pd.DataFrame) -> Dict[str, Any]:
    buys, sells = _prepare_rows(canon_df)

    scrips = sorted(canon_df["scrip"].unique())
    realized_rows: List[Dict[str, Any]] = []
    remaining_lots: List[Tuple[str, BuyLot]] = []

    for s in scrips:
        b = buys[buys["scrip"] == s]
        s_df = sells[sells["scrip"] == s]
        if b.empty and s_df.empty:
            continue
        realized, lots = _fifo_match_for_scrip(b, s_df, s)
        realized_rows.extend(realized)
        for l in lots:
            remaining_lots.append((s, l))

    realized_df = pd.DataFrame(realized_rows)
    if realized_df.empty:
        realized_df = pd.DataFrame(
            columns=[
                "Scrip",
                "BuyDate",
                "SellDate",
                "Qty",
                "HoldingDays",
                "Term",
                "BuyUnitCost",
                "BuyCostTotal",
                "SellUnitPrice",
                "SellProceedsGross",
                "SellCostsAllocated",
                "SellProceedsNet",
                "Gain",
                "BuyRef",
                "SellRef",
            ]
        )

    # Per-scrip summary
    def agg_term(df: pd.DataFrame, term: str) -> float:
        return df.loc[df["Term"] == term, "Gain"].sum()

    per_scrip = (
        realized_df.groupby("Scrip").apply(
            lambda g: pd.Series(
                {
                    "STCG_Total": agg_term(g, "ST"),
                    "LTCG_Total": agg_term(g, "LT"),
                    "Net_Total_Gain": g["Gain"].sum(),
                    "Total_Sell_Proceeds": g["SellProceedsNet"].sum(),
                    "Total_Buy_Cost": g["BuyCostTotal"].sum(),
                    "#Sells": g["SellRef"].nunique(),
                    "#MatchedLots": len(g),
                }
            )
        ).reset_index()
        if not realized_df.empty
        else pd.DataFrame(
            columns=[
                "Scrip",
                "STCG_Total",
                "LTCG_Total",
                "Net_Total_Gain",
                "Total_Sell_Proceeds",
                "Total_Buy_Cost",
                "#Sells",
                "#MatchedLots",
            ]
        )
    )

    overall = pd.DataFrame(
        [
            {
                "STCG_Total": per_scrip["STCG_Total"].sum() if not per_scrip.empty else 0.0,
                "LTCG_Total": per_scrip["LTCG_Total"].sum() if not per_scrip.empty else 0.0,
                "Net_Total_Gain": per_scrip["Net_Total_Gain"].sum() if not per_scrip.empty else 0.0,
                "Total_Sell_Proceeds": per_scrip["Total_Sell_Proceeds"].sum() if not per_scrip.empty else 0.0,
                "Total_Buy_Cost": per_scrip["Total_Buy_Cost"].sum() if not per_scrip.empty else 0.0,
            }
        ]
    )

    # Open positions
    open_rows: List[Dict[str, Any]] = []
    asof = max(canon_df["trade_date"]) if not canon_df.empty else date.today()
    for s, l in remaining_lots:
        open_rows.append(
            {
                "Scrip": s,
                "BuyDate": l.buy_date,
                "QtyRemaining": l.qty_remaining,
                "UnitCost": l.unit_cost,
                "TotalCost": l.qty_remaining * l.unit_cost,
                "AgeDays": (asof - l.buy_date).days,
            }
        )
    open_df = pd.DataFrame(open_rows)
    if open_df.empty:
        open_df = pd.DataFrame(columns=["Scrip", "BuyDate", "QtyRemaining", "UnitCost", "TotalCost", "AgeDays"])

    return {
        "realized_lots": realized_df,
        "per_scrip_summary": per_scrip,
        "overall_summary": overall,
        "open_positions": open_df,
    }
