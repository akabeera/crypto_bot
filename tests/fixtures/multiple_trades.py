import json

SOL_TRADES_JSON = """[
  {
    "_id": {
      "$oid": "64cd37f1f9faac73fb4fe307"
    },
    "info": {
      "order_id": "06256e71-3ee6-496a-aa26-61101f40a76e",
      "product_id": "SOL-USD",
      "user_id": "2f8f60ef-ab3b-5b85-bf17-af6dfd6df4ef",
      "order_configuration": {
        "market_market_ioc": {
          "quote_size": "5"
        }
      },
      "side": "BUY",
      "client_order_id": "ae10c573-24d2-4d46-8d58-6feca882a453",
      "status": "FILLED",
      "time_in_force": "IMMEDIATE_OR_CANCEL",
      "created_time": "2023-08-04T17:40:00.228226Z",
      "completion_percentage": "100",
      "filled_size": "0.2132552648459785",
      "average_filled_price": "23.2600000000000018",
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
      "last_fill_time": "2023-08-04T17:40:00.355196543Z"
    },
    "id": "06256e71-3ee6-496a-aa26-61101f40a76e",
    "clientOrderId": "ae10c573-24d2-4d46-8d58-6feca882a453",
    "timestamp": {
      "$numberLong": "1691170800228"
    },
    "datetime": "2023-08-04T17:40:00.228226Z",
    "lastTradeTimestamp": null,
    "symbol": "SOL/USD",
    "type": "market",
    "timeInForce": "IOC",
    "postOnly": false,
    "side": "buy",
    "price": 23.26,
    "stopPrice": null,
    "triggerPrice": null,
    "amount": 0.2132552648459785,
    "filled": 0.2132552648459785,
    "remaining": 0,
    "cost": 4.9603174603174605,
    "average": 23.26,
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
  },
  {
    "_id": {
      "$oid": "64cd38a5007a878aeb247cda"
    },
    "info": {
      "order_id": "f03650af-a426-4504-a98f-63d14d3ae1f6",
      "product_id": "SOL-USD",
      "user_id": "2f8f60ef-ab3b-5b85-bf17-af6dfd6df4ef",
      "order_configuration": {
        "market_market_ioc": {
          "quote_size": "5"
        }
      },
      "side": "BUY",
      "client_order_id": "431d3a82-4554-4e70-be71-0c29d494d7dc",
      "status": "FILLED",
      "time_in_force": "IMMEDIATE_OR_CANCEL",
      "created_time": "2023-08-04T17:43:00.875434Z",
      "completion_percentage": "100",
      "filled_size": "0.2133469875405359",
      "average_filled_price": "23.2500000000000029",
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
      "last_fill_time": "2023-08-04T17:43:00.991970075Z"
    },
    "id": "f03650af-a426-4504-a98f-63d14d3ae1f6",
    "clientOrderId": "431d3a82-4554-4e70-be71-0c29d494d7dc",
    "timestamp": {
      "$numberLong": "1691170980875"
    },
    "datetime": "2023-08-04T17:43:00.875434Z",
    "lastTradeTimestamp": null,
    "symbol": "SOL/USD",
    "type": "market",
    "timeInForce": "IOC",
    "postOnly": false,
    "side": "buy",
    "price": 23.250000000000004,
    "stopPrice": null,
    "triggerPrice": null,
    "amount": 0.2133469875405359,
    "filled": 0.2133469875405359,
    "remaining": 0,
    "cost": 4.9603174603174605,
    "average": 23.250000000000004,
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
  },
  {
    "_id": {
      "$oid": "64cd3dcb805ba66a2632db9c"
    },
    "info": {
      "order_id": "3961a397-bd84-4c21-a3b0-7f7131055246",
      "product_id": "SOL-USD",
      "user_id": "2f8f60ef-ab3b-5b85-bf17-af6dfd6df4ef",
      "order_configuration": {
        "market_market_ioc": {
          "quote_size": "5"
        }
      },
      "side": "BUY",
      "client_order_id": "acd55b2f-cf4b-4b48-81bf-80be9028a9a8",
      "status": "FILLED",
      "time_in_force": "IMMEDIATE_OR_CANCEL",
      "created_time": "2023-08-04T18:04:58.277204Z",
      "completion_percentage": "100",
      "filled_size": "0.2136226296433015",
      "average_filled_price": "23.2199999999999975",
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
      "last_fill_time": "2023-08-04T18:04:58.389121598Z"
    },
    "id": "3961a397-bd84-4c21-a3b0-7f7131055246",
    "clientOrderId": "acd55b2f-cf4b-4b48-81bf-80be9028a9a8",
    "timestamp": {
      "$numberLong": "1691172298277"
    },
    "datetime": "2023-08-04T18:04:58.277204Z",
    "lastTradeTimestamp": null,
    "symbol": "SOL/USD",
    "type": "market",
    "timeInForce": "IOC",
    "postOnly": false,
    "side": "buy",
    "price": 23.22,
    "stopPrice": null,
    "triggerPrice": null,
    "amount": 0.2136226296433015,
    "filled": 0.2136226296433015,
    "remaining": 0,
    "cost": 4.9603174603174605,
    "average": 23.22,
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
  },
  {
    "_id": {
      "$oid": "64cd46e60fb645c6ffde0555"
    },
    "info": {
      "order_id": "aac5b7bf-cdde-42c9-8241-bb38ab646ed2",
      "product_id": "SOL-USD",
      "user_id": "2f8f60ef-ab3b-5b85-bf17-af6dfd6df4ef",
      "order_configuration": {
        "market_market_ioc": {
          "quote_size": "5"
        }
      },
      "side": "BUY",
      "client_order_id": "93ba5ccc-c46c-4bf8-a48e-7373fd148eee",
      "status": "FILLED",
      "time_in_force": "IMMEDIATE_OR_CANCEL",
      "created_time": "2023-08-04T18:43:49.572898Z",
      "completion_percentage": "100",
      "filled_size": "0.2158536753837015",
      "average_filled_price": "22.9799999999999992",
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
      "last_fill_time": "2023-08-04T18:43:49.687550538Z"
    },
    "id": "aac5b7bf-cdde-42c9-8241-bb38ab646ed2",
    "clientOrderId": "93ba5ccc-c46c-4bf8-a48e-7373fd148eee",
    "timestamp": {
      "$numberLong": "1691174629572"
    },
    "datetime": "2023-08-04T18:43:49.572898Z",
    "lastTradeTimestamp": null,
    "symbol": "SOL/USD",
    "type": "market",
    "timeInForce": "IOC",
    "postOnly": false,
    "side": "buy",
    "price": 22.98,
    "stopPrice": null,
    "triggerPrice": null,
    "amount": 0.2158536753837015,
    "filled": 0.2158536753837015,
    "remaining": 0,
    "cost": 4.9603174603174605,
    "average": 22.98,
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
  }
]
"""

ATOM_TRADES_JSON = """[
  {
    "_id": {
      "$oid": "652f474a6b0cd2569d93a684"
    },
    "info": {
      "order_id": "c3309fa2-e4fa-4225-9bae-3c4e511d189b",
      "product_id": "ATOM-USD",
      "user_id": "2f8f60ef-ab3b-5b85-bf17-af6dfd6df4ef",
      "order_configuration": {
        "market_market_ioc": {
          "quote_size": "5"
        }
      },
      "side": "BUY",
      "client_order_id": "b23a522f-af31-4811-9920-c94b35c2555a",
      "status": "FILLED",
      "time_in_force": "IMMEDIATE_OR_CANCEL",
      "created_time": "2023-10-18T02:47:38.134498Z",
      "completion_percentage": "100",
      "filled_size": "0.7780707905922838",
      "average_filled_price": "6.3910000000000002",
      "fee": "",
      "number_of_fills": "2",
      "filled_value": "4.9726504226752859",
      "pending_cancel": false,
      "size_in_quote": true,
      "total_fees": "0.0273495773247141",
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
      "last_fill_time": "2023-10-18T02:47:38.267308916Z",
      "edit_history": [],
      "leverage": "",
      "margin_type": "UNKNOWN_MARGIN_TYPE"
    },
    "id": "c3309fa2-e4fa-4225-9bae-3c4e511d189b",
    "clientOrderId": "b23a522f-af31-4811-9920-c94b35c2555a",
    "timestamp": {
      "$numberLong": "1697597258134"
    },
    "datetime": "2023-10-18T02:47:38.134498Z",
    "lastTradeTimestamp": null,
    "symbol": "ATOM/USD",
    "type": "market",
    "timeInForce": "IOC",
    "postOnly": false,
    "side": "buy",
    "price": 6.391,
    "stopPrice": null,
    "triggerPrice": null,
    "amount": 0.7780707905922838,
    "filled": 0.7780707905922838,
    "remaining": 0,
    "cost": 4.972650422675286,
    "average": 6.391,
    "status": "closed",
    "fee": {
      "cost": 0.0273495773247141,
      "currency": null
    },
    "trades": [],
    "fees": [
      {
        "cost": 0.0273495773247141,
        "currency": null
      }
    ],
    "lastUpdateTimestamp": null,
    "reduceOnly": null,
    "takeProfitPrice": null,
    "stopLossPrice": null
  },
  {
    "_id": {
      "$oid": "652fecb86b0cd2569d93a68b"
    },
    "info": {
      "order_id": "75257129-3420-4668-8bc7-b8aeafc879b3",
      "product_id": "ATOM-USD",
      "user_id": "2f8f60ef-ab3b-5b85-bf17-af6dfd6df4ef",
      "order_configuration": {
        "market_market_ioc": {
          "quote_size": "5"
        }
      },
      "side": "BUY",
      "client_order_id": "7041edb4-fefe-4d8c-b069-1c9fc85f4598",
      "status": "FILLED",
      "time_in_force": "IMMEDIATE_OR_CANCEL",
      "created_time": "2023-10-18T14:33:27.133850Z",
      "completion_percentage": "100",
      "filled_size": "0.7838351864242254",
      "average_filled_price": "6.344",
      "fee": "",
      "number_of_fills": "2",
      "filled_value": "4.9726504226752859",
      "pending_cancel": false,
      "size_in_quote": true,
      "total_fees": "0.0273495773247141",
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
      "last_fill_time": "2023-10-18T14:33:27.244706056Z",
      "edit_history": [],
      "leverage": "",
      "margin_type": "UNKNOWN_MARGIN_TYPE"
    },
    "id": "75257129-3420-4668-8bc7-b8aeafc879b3",
    "clientOrderId": "7041edb4-fefe-4d8c-b069-1c9fc85f4598",
    "timestamp": {
      "$numberLong": "1697639607133"
    },
    "datetime": "2023-10-18T14:33:27.133850Z",
    "lastTradeTimestamp": null,
    "symbol": "ATOM/USD",
    "type": "market",
    "timeInForce": "IOC",
    "postOnly": false,
    "side": "buy",
    "price": 6.344,
    "stopPrice": null,
    "triggerPrice": null,
    "amount": 0.7838351864242254,
    "filled": 0.7838351864242254,
    "remaining": 0,
    "cost": 4.972650422675286,
    "average": 6.344,
    "status": "closed",
    "fee": {
      "cost": 0.0273495773247141,
      "currency": null
    },
    "trades": [],
    "fees": [
      {
        "cost": 0.0273495773247141,
        "currency": null
      }
    ],
    "lastUpdateTimestamp": null,
    "reduceOnly": null,
    "takeProfitPrice": null,
    "stopLossPrice": null
  },
  {
    "_id": {
      "$oid": "65302b6a6b0cd2569d93a68c"
    },
    "info": {
      "order_id": "4d0c06e8-0971-429b-9026-c1b136a22c26",
      "product_id": "ATOM-USD",
      "user_id": "2f8f60ef-ab3b-5b85-bf17-af6dfd6df4ef",
      "order_configuration": {
        "market_market_ioc": {
          "quote_size": "5"
        }
      },
      "side": "BUY",
      "client_order_id": "d881fb7b-7027-4c45-884e-e358fe7ee84e",
      "status": "FILLED",
      "time_in_force": "IMMEDIATE_OR_CANCEL",
      "created_time": "2023-10-18T19:00:57.119365Z",
      "completion_percentage": "100",
      "filled_size": "0.7863141085824298",
      "average_filled_price": "6.3239999999999998",
      "fee": "",
      "number_of_fills": "2",
      "filled_value": "4.9726504226752859",
      "pending_cancel": false,
      "size_in_quote": true,
      "total_fees": "0.0273495773247141",
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
      "last_fill_time": "2023-10-18T19:00:57.244118054Z",
      "edit_history": [],
      "leverage": "",
      "margin_type": "UNKNOWN_MARGIN_TYPE"
    },
    "id": "4d0c06e8-0971-429b-9026-c1b136a22c26",
    "clientOrderId": "d881fb7b-7027-4c45-884e-e358fe7ee84e",
    "timestamp": {
      "$numberLong": "1697655657119"
    },
    "datetime": "2023-10-18T19:00:57.119365Z",
    "lastTradeTimestamp": null,
    "symbol": "ATOM/USD",
    "type": "market",
    "timeInForce": "IOC",
    "postOnly": false,
    "side": "buy",
    "price": 6.324,
    "stopPrice": null,
    "triggerPrice": null,
    "amount": 0.7863141085824298,
    "filled": 0.7863141085824298,
    "remaining": 0,
    "cost": 4.972650422675286,
    "average": 6.324,
    "status": "closed",
    "fee": {
      "cost": 0.0273495773247141,
      "currency": null
    },
    "trades": [],
    "fees": [
      {
        "cost": 0.0273495773247141,
        "currency": null
      }
    ],
    "lastUpdateTimestamp": null,
    "reduceOnly": null,
    "takeProfitPrice": null,
    "stopLossPrice": null
  },
  {
    "_id": {
      "$oid": "653039916b0cd2569d93a68d"
    },
    "info": {
      "order_id": "827ae681-c568-4989-a3e5-d6b9c33388c5",
      "product_id": "ATOM-USD",
      "user_id": "2f8f60ef-ab3b-5b85-bf17-af6dfd6df4ef",
      "order_configuration": {
        "market_market_ioc": {
          "quote_size": "5"
        }
      },
      "side": "BUY",
      "client_order_id": "8d6744eb-752d-4c31-af4d-e10b337ee739",
      "status": "FILLED",
      "time_in_force": "IMMEDIATE_OR_CANCEL",
      "created_time": "2023-10-18T20:01:19.897251Z",
      "completion_percentage": "100",
      "filled_size": "0.7894348980275101",
      "average_filled_price": "6.2989999999999997",
      "fee": "",
      "number_of_fills": "2",
      "filled_value": "4.9726504226752859",
      "pending_cancel": false,
      "size_in_quote": true,
      "total_fees": "0.0273495773247141",
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
      "last_fill_time": "2023-10-18T20:01:20.035295849Z",
      "edit_history": [],
      "leverage": "",
      "margin_type": "UNKNOWN_MARGIN_TYPE"
    },
    "id": "827ae681-c568-4989-a3e5-d6b9c33388c5",
    "clientOrderId": "8d6744eb-752d-4c31-af4d-e10b337ee739",
    "timestamp": {
      "$numberLong": "1697659279897"
    },
    "datetime": "2023-10-18T20:01:19.897251Z",
    "lastTradeTimestamp": null,
    "symbol": "ATOM/USD",
    "type": "market",
    "timeInForce": "IOC",
    "postOnly": false,
    "side": "buy",
    "price": 6.2989999999999995,
    "stopPrice": null,
    "triggerPrice": null,
    "amount": 0.7894348980275101,
    "filled": 0.7894348980275101,
    "remaining": 0,
    "cost": 4.972650422675286,
    "average": 6.2989999999999995,
    "status": "closed",
    "fee": {
      "cost": 0.0273495773247141,
      "currency": null
    },
    "trades": [],
    "fees": [
      {
        "cost": 0.0273495773247141,
        "currency": null
      }
    ],
    "lastUpdateTimestamp": null,
    "reduceOnly": null,
    "takeProfitPrice": null,
    "stopLossPrice": null
  },
  {
    "_id": {
      "$oid": "65308848af7cd453115229f6"
    },
    "info": {
      "order_id": "1e198760-5c07-453d-9f05-37911371f558",
      "product_id": "ATOM-USD",
      "user_id": "2f8f60ef-ab3b-5b85-bf17-af6dfd6df4ef",
      "order_configuration": {
        "market_market_ioc": {
          "quote_size": "5"
        }
      },
      "side": "BUY",
      "client_order_id": "a9606541-bd9b-4a51-ad82-881c4d554ea5",
      "status": "FILLED",
      "time_in_force": "IMMEDIATE_OR_CANCEL",
      "created_time": "2023-10-19T01:37:11.388631Z",
      "completion_percentage": "100",
      "filled_size": "0.7965161657336675",
      "average_filled_price": "6.2429999999999996",
      "fee": "",
      "number_of_fills": "2",
      "filled_value": "4.9726504226752859",
      "pending_cancel": false,
      "size_in_quote": true,
      "total_fees": "0.0273495773247141",
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
      "last_fill_time": "2023-10-19T01:37:11.516862427Z",
      "edit_history": [],
      "leverage": "",
      "margin_type": "UNKNOWN_MARGIN_TYPE"
    },
    "id": "1e198760-5c07-453d-9f05-37911371f558",
    "clientOrderId": "a9606541-bd9b-4a51-ad82-881c4d554ea5",
    "timestamp": {
      "$numberLong": "1697679431388"
    },
    "datetime": "2023-10-19T01:37:11.388631Z",
    "lastTradeTimestamp": null,
    "symbol": "ATOM/USD",
    "type": "market",
    "timeInForce": "IOC",
    "postOnly": false,
    "side": "buy",
    "price": 6.242999999999999,
    "stopPrice": null,
    "triggerPrice": null,
    "amount": 0.7965161657336675,
    "filled": 0.7965161657336675,
    "remaining": 0,
    "cost": 4.972650422675286,
    "average": 6.242999999999999,
    "status": "closed",
    "fee": {
      "cost": 0.0273495773247141,
      "currency": null
    },
    "trades": [],
    "fees": [
      {
        "cost": 0.0273495773247141,
        "currency": null
      }
    ],
    "lastUpdateTimestamp": null,
    "reduceOnly": null,
    "takeProfitPrice": null,
    "stopLossPrice": null
  }
]
"""


ATOM_TRADES = json.loads(ATOM_TRADES_JSON)
SOL_TRADES = json.loads(SOL_TRADES_JSON)