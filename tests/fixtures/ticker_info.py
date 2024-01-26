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

ATOM_TICKER_INFO = json.loads(ATOM_TICKER_INFO_JSON)