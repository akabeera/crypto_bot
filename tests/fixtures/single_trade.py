import json

ATOM_TRADE_JSON = """{
    "info": {
      "order_id": "a6b876b9-af4b-5f3a-88f0-4f129e7ce33e",
      "product_id": "ATOM-USD",
      "user_id": "2f8f60ef-bb3b-6b85-bf20-af6dfd6df9ef",
      "order_configuration": {
        "market_market_ioc": {
          "quote_size": "5"
        }
      },
      "side": "BUY",
      "client_order_id": "2936f079-1273-0a7b-8b0e-261f6a387a56",
      "status": "FILLED",
      "time_in_force": "IMMEDIATE_OR_CANCEL",
      "created_time": "2023-08-04T18:05:21.234994Z",
      "completion_percentage": "100",
      "filled_size": "0.5770494951509377",
      "average_filled_price": "8.5959999999999997",
      "fee": "",
      "number_of_fills": "2",
      "filled_value": "4.9603174603174603",
      "pending_cancel": false,
      "size_in_quote": true,
      "total_fees": "0.0396825396825397",
      "size_inclusive_of_fees": true,
      "total_value_after_fees": "5",
      "trigger_status": "INVALID_ORDER_TYPE",
      "order_type": "MARKET",
      "reject_reason": "REJECT_REASON_UNSPECIFIED",
      "settled": true,
      "product_type": "SPOT",
      "reject_message": "",
      "cancel_message": "Internal error",
      "order_placement_source": "RETAIL_ADVANCED",
      "outstanding_hold_amount": "0",
      "is_liquidation": false,
      "last_fill_time": "2023-08-04T18:05:21.351596698Z"
    },
    "id": "b0b876b0-fc4a-4f39-80f0-2f129d7cc33e",
    "clientOrderId": "1836f07a-0275-4c3b-8d0e-261f6a387d05",
    "timestamp": 1691172321234,
    "datetime": "2023-08-04T18:05:21.234994Z",
    "lastTradeTimestamp": null,
    "symbol": "ATOM/USD",
    "type": "market",
    "timeInForce": "IOC",
    "postOnly": false,
    "side": "buy",
    "price": 8.596,
    "stopPrice": null,
    "triggerPrice": null,
    "amount": 0.5770494951509377,
    "filled": 0.5770494951509377,
    "remaining": 0,
    "cost": 4.9603174603174605,
    "average": 8.596,
    "status": "closed",
    "fee": {
      "cost": 0.0396825396825397,
      "currency": null
    },
    "trades": [],
    "fees": [
      {
        "cost": 0.0396825396825397,
        "currency": null
      }
    ],
    "lastUpdateTimestamp": null,
    "reduceOnly": null,
    "takeProfitPrice": null,
    "stopLossPrice": null
  }"""

ATOM_TRADE = json.loads(ATOM_TRADE_JSON)

