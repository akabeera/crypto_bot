import json

SOL_TICKER_PAIR = "SOL/USD"
ATOM_TICKER_PAIR = "ATOM/USD"

ATOM_TICKER_INFO_JSON = """{
    "symbol": "ATOM/USD", 
    "timestamp": 1698926118870,
    "datetime": "2023-11-02T11:55:18.870307Z",
    "bid": 7.94, 
    "ask": 7.94, 
    "last": 7.94, 
    "high": null, 
    "low": null,
    "bidVolume": null,
    "askVolume": null,
    "vwap": null,
    "open": null, 
    "close": 7.94,
    "previousClose": null,
    "change": null,
    "percentage": null,
    "average": null,
    "baseVolume": null,
    "quoteVolume": null,
    "info": {
        "trade_id": "573903061", 
        "product_id": "ATOM-USD",
        "price": "7.94", 
        "size": "1",
        "time": "2023-11-02T11:55:18.870307Z",
        "side": "SELL",
        "bid": "",
        "ask": ""
    }
}"""

MATIC_TICKER_INFO_JSON = """{
  "symbol": "MATIC/USD",
  "timestamp": 1707151209630,
  "datetime": "2024-02-05T16:40:09.630621Z",
  "bid": 0.7797,
  "ask": 0.7798,
  "last": 0.7799,
  "high": null,
  "low": null,
  "bidVolume": null,
  "askVolume": null,
  "vwap": null,
  "open": null,
  "close": 0.7799,
  "previousClose": null,
  "change": null,
  "percentage": null,
  "average": null,
  "baseVolume": null,
  "quoteVolume": null,
  "info": {
    "trade_id": "79899061",
    "product_id": "MATIC-USD",
    "price": "0.7799",
    "size": "3278.4",
    "time": "2024-02-05T16:40:09.630621Z",
    "side": "BUY",
    "bid": "",
    "ask": ""
  }
}
"""

ATOM_TICKER_INFO = json.loads(ATOM_TICKER_INFO_JSON)
MATIC_TICKER_INFO = json.loads(MATIC_TICKER_INFO_JSON) 