
import unittest
import mongomock

from decimal import *
from utils.mongodb_service import MongoDBService
from utils.constants import QUANTIZING_DECIMAL
from utils.constants import DEFAULT_MONGO_DB_NAME, DEFAULT_MONGO_SELL_ORDERS_COLLECTION, DEFAULT_MONGO_TRADES_COLLECTION
from utils.trading import calculate_profit_percent, calculate_avg_position, find_profitable_trades, TakeProfitEvaluationType
from tests.fixtures.single_trade import ATOM_TRADE
from tests.fixtures.multiple_trades import SOL_TRADES, MATIC_TRADES
from tests.fixtures.ticker_info import ATOM_TICKER_INFO, MATIC_TICKER_INFO

class TestUtils(unittest.TestCase):

    def setUp(self):
        # Create a mongomock database
        self.mock_db = mongomock.MongoClient().db
        self.mongodb_service = MongoDBService("mongomock://localhost", DEFAULT_MONGO_DB_NAME, self.mock_db)

        docs_to_insert = MATIC_TRADES
        for doc in docs_to_insert:
            self.mongodb_service.insert_one(DEFAULT_MONGO_TRADES_COLLECTION, doc)

    def tearDown(self):
        self.mongodb_service.delete_many(DEFAULT_MONGO_TRADES_COLLECTION)
        self.mongodb_service.delete_many(DEFAULT_MONGO_SELL_ORDERS_COLLECTION)

    def test_rounding_down_shares(self):
        shares: float = 2091.2128288757876989
        rounded_shares = float(Decimal(shares).quantize(QUANTIZING_DECIMAL, rounding=ROUND_DOWN))
        expected_rounded_shares: float = 2091.212828875787
        self.assertEqual(rounded_shares, expected_rounded_shares)


    def test_calculate_profit_percent_loss(self):
        expected_profit = Decimal(-0.0836454017003109).quantize(QUANTIZING_DECIMAL, rounding=ROUND_UP)
        avg_position = ATOM_TRADE
        ticker_info = ATOM_TICKER_INFO
        profit = calculate_profit_percent(avg_position, ticker_info["bid"]).quantize(QUANTIZING_DECIMAL, rounding=ROUND_UP)
        self.assertEqual(profit.normalize(), expected_profit)

    def test_calculate_avg_position(self):
        trades = SOL_TRADES

        expected_shares = 0.8560785574135173
        expected_fee = 0.1587301587301588
        expected_cost = 19.841269841269842
        expected_price = 23.176926544237435

        avg_position = calculate_avg_position(trades)

        self.assertEqual(avg_position["filled"], expected_shares)
        self.assertEqual(avg_position["amount"], expected_shares)
        self.assertEqual(avg_position["fee"]["cost"], expected_fee)
        self.assertEqual(avg_position["cost"], expected_cost)
        self.assertEqual(avg_position["price"], expected_price)
        self.assertEqual(avg_position["average"], expected_price)

    def test_find_profitable_trades_with_individual_lots(self):
        ticker_pair = "MATIC/USD"

        filter = {
            "symbol": ticker_pair
        }
        all_positions = self.mongodb_service.query(DEFAULT_MONGO_TRADES_COLLECTION, filter)

        avg_position = calculate_avg_position(all_positions)
        expected_avg_cost = 0.9252259314938164

        self.assertAlmostEqual(avg_position["price"], expected_avg_cost)
        self.assertAlmostEqual(avg_position["average"], expected_avg_cost)

        take_profit_threshold = Decimal(2.5/100)
        take_profit_evaluation_type = TakeProfitEvaluationType.INDIVIDUAL_LOTS

        ticker_info = MATIC_TICKER_INFO

        profitable_positions_to_exit = find_profitable_trades(ticker_pair, 
                                                              avg_position, 
                                                              all_positions, 
                                                              ticker_info, 
                                                              take_profit_threshold, 
                                                              take_profit_evaluation_type)
        

        expected_number_of_positions_to_exit = 5
        self.assertEqual(len(profitable_positions_to_exit), expected_number_of_positions_to_exit)

        expected_positions_ids_to_exit = ["8ac75077-288e-4bef-9d69-4748ebdc9b04", "5a3a64a2-edff-4ef1-9097-7d6937661aa9", "01808f74-cdbc-4754-9bd5-ef28ac5c9cee", "58cfebc5-c4d9-4458-b6a6-12603793a9f7", "56e22ae5-dea7-4fa5-88d6-910291d3188e"] 
        position_ids_to_exit = []
        for pos in profitable_positions_to_exit:
            position_ids_to_exit.append(pos["id"])

        self.assertEqual(set(position_ids_to_exit), set(expected_positions_ids_to_exit))

    def test_find_profitable_trades_with_average_position(self):
        ticker_pair = "MATIC/USD"

        filter = {
            "symbol": ticker_pair
        }
        all_positions = self.mongodb_service.query(DEFAULT_MONGO_TRADES_COLLECTION, filter)

        avg_position = calculate_avg_position(all_positions)

    

if __name__ == '__main__':
    unittest.main()