import pandas as pd
from datetime import date, timedelta

from app.core.engine import process_transactions


def df_from(rows):
    return pd.DataFrame(rows)


def base_row(td, scrip, action, qty, price, b=0, c=0, stt=0, rid=0):
    return {
        'trade_date': td,
        'scrip': scrip,
        'action': action,
        'quantity': qty,
        'price': price,
        'brokerage': b,
        'charges': c,
        'stt': stt,
        'exchange': '',
        'isin': '',
        'notes': '',
        'source_row_id': rid,
    }


def test_partial_sells_multiple_buys():
    # Two buys, one sell that spans both
    rows = [
        base_row(date(2023,1,1), 'TCS', 'BUY', 100, 100, b=10, c=0, rid=1),
        base_row(date(2023,1,10), 'TCS', 'BUY', 100, 200, b=10, c=0, rid=2),
        base_row(date(2023,2,1), 'TCS', 'SELL', 150, 150, b=10, c=0, stt=5, rid=3),
    ]
    res = process_transactions(df_from(rows))
    rl = res['realized_lots']
    # Expect two realized rows: 100 from first lot, 50 from second
    assert len(rl) == 2
    assert rl.iloc[0]['Qty'] == 100
    assert rl.iloc[1]['Qty'] == 50
    # Costs: first buy unit cost = (100*100+10)/100 = 100.1
    assert round(rl.iloc[0]['BuyUnitCost'], 4) == 100.1
    # Sell costs pro-rata by qty: total costs 10+0+5=15 => per share 0.1
    assert round((rl['SellCostsAllocated'].sum())/150, 4) == 0.1


def test_sell_exceeds_buys_errors():
    rows = [
        base_row(date(2023,1,1), 'INFY', 'BUY', 10, 100, rid=1),
        base_row(date(2023,1,2), 'INFY', 'SELL', 20, 100, rid=2),
    ]
    try:
        process_transactions(df_from(rows))
        assert False, 'Expected ValueError'
    except ValueError as e:
        assert 'exceeds available buys' in str(e)


def test_365_day_boundary():
    buy_date = date(2023,1,1)
    sell_date = buy_date + timedelta(days=365)
    rows = [
        base_row(buy_date, 'TCS', 'BUY', 1, 100, rid=1),
        base_row(sell_date, 'TCS', 'SELL', 1, 200, rid=2),
    ]
    res = process_transactions(df_from(rows))
    rl = res['realized_lots']
    assert len(rl) == 1
    assert rl.iloc[0]['HoldingDays'] == 365
    assert rl.iloc[0]['Term'] == 'LT'

