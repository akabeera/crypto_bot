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

MATIC_TRADE1_JSON = """
{

  "info": {
    "order_id": "b04b4baa-af07-40f6-9a7d-e02e4b4eda97",
    "product_id": "MATIC-USD",
    "user_id": "2f8f60ef-ab3b-5b85-bf17-af6dfd6df4ef",
    "order_configuration": {
      "market_market_ioc": {
        "quote_size": "50"
      }
    },
    "side": "BUY",
    "client_order_id": "f4d6948f-787d-406b-b8e1-09f74c3e79fd",
    "status": "FILLED",
    "time_in_force": "IMMEDIATE_OR_CANCEL",
    "created_time": "2024-01-02T19:27:11.065094Z",
    "completion_percentage": "100",
    "filled_size": "51.322609303044098",
    "average_filled_price": "0.9718",
    "fee": "",
    "number_of_fills": "2",
    "filled_value": "49.8753117206982544",
    "pending_cancel": false,
    "size_in_quote": true,
    "total_fees": "0.1246882793017456",
    "size_inclusive_of_fees": true,
    "total_value_after_fees": "50",
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
    "last_fill_time": "2024-01-02T19:27:11.183947189Z",
    "edit_history": [],
    "leverage": "",
    "margin_type": "UNKNOWN_MARGIN_TYPE"
  },
  "id": "b04b4baa-af07-40f6-9a7d-e02e4b4eda97",
  "clientOrderId": "f4d6948f-787d-406b-b8e1-09f74c3e79fd",
  "timestamp": 1704223631065,
  "datetime": "2024-01-02T19:27:11.065094Z",
  "lastTradeTimestamp": null,
  "symbol": "MATIC/USD",
  "type": "market",
  "timeInForce": "IOC",
  "postOnly": false,
  "side": "buy",
  "price": 0.9718,
  "stopPrice": null,
  "triggerPrice": null,
  "amount": 51.322609303044096,
  "filled": 51.322609303044096,
  "remaining": 0,
  "cost": 49.87531172069826,
  "average": 0.9718,
  "status": "closed",
  "fee": {
    "cost": 0.1246882793017456,
    "currency": null
  },
  "trades": [],
  "fees": [
    {
      "cost": 0.1246882793017456,
      "currency": null
    }
  ],
  "lastUpdateTimestamp": null,
  "reduceOnly": null,
  "takeProfitPrice": null,
  "stopLossPrice": null
}
"""

MATIC_TRADE2_JSON =  """
{
  "info": {
    "order_id": "5021c67f-17ea-47fb-84ed-043fbc7820cc",
    "product_id": "MATIC-USD",
    "user_id": "2f8f60ef-ab3b-5b85-bf17-af6dfd6df4ef",
    "order_configuration": {
      "market_market_ioc": {
        "quote_size": "20"
      }
    },
    "side": "BUY",
    "client_order_id": "177f7d9d-af40-4e5d-b697-f9d66065f40a",
    "status": "FILLED",
    "time_in_force": "IMMEDIATE_OR_CANCEL",
    "created_time": "2024-01-03T14:16:54.410799Z",
    "completion_percentage": "100",
    "filled_size": "23.5066863300097817",
    "average_filled_price": "0.8487",
    "fee": "",
    "number_of_fills": "2",
    "filled_value": "19.9501246882793017",
    "pending_cancel": false,
    "size_in_quote": true,
    "total_fees": "0.0498753117206983",
    "size_inclusive_of_fees": true,
    "total_value_after_fees": "20",
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
    "last_fill_time": "2024-01-03T14:16:54.525195055Z",
    "edit_history": [],
    "leverage": "",
    "margin_type": "UNKNOWN_MARGIN_TYPE"
  },
  "id": "5021c67f-17ea-47fb-84ed-043fbc7820cc",
  "clientOrderId": "177f7d9d-af40-4e5d-b697-f9d66065f40a",
  "timestamp": 1704291414410,
  "datetime": "2024-01-03T14:16:54.410799Z",
  "lastTradeTimestamp": null,
  "symbol": "MATIC/USD",
  "type": "market",
  "timeInForce": "IOC",
  "postOnly": false,
  "side": "buy",
  "price": 0.8487,
  "stopPrice": null,
  "triggerPrice": null,
  "amount": 23.50668633000978,
  "filled": 23.50668633000978,
  "remaining": 0,
  "cost": 19.950124688279303,
  "average": 0.8487,
  "status": "closed",
  "fee": {
    "cost": 0.0498753117206983,
    "currency": null
  },
  "trades": [],
  "fees": [
    {
      "cost": 0.0498753117206983,
      "currency": null
    }
  ],
  "lastUpdateTimestamp": null,
  "reduceOnly": null,
  "takeProfitPrice": null,
  "stopLossPrice": null
}
"""
ATOM_TRADE = json.loads(ATOM_TRADE_JSON)
MATIC_TRADE1 = json.loads(MATIC_TRADE1_JSON)
MATIC_TRADE2 = json.loads(MATIC_TRADE2_JSON)

