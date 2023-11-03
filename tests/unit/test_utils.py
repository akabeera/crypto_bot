
import unittest
from decimal import *
from strategies.utils import calculate_profit_percent, calculate_avg_position
from tests.fixtures.single_trade import ATOM_TRADE
from tests.fixtures.multiple_trades import SOL_TRADES
from tests.fixtures.ticker_info import ATOM_TICKER_INFO

MAX_PRECISION = 12

class TestUtils(unittest.TestCase):

    quantizing_decimal = Decimal(1).scaleb(-MAX_PRECISION)

    def test_calculate_profit_percent_loss(self):
        expected_profit = Decimal(-0.09231456491391342377614447500).quantize(TestUtils.quantizing_decimal, rounding=ROUND_UP)
        avg_position = ATOM_TRADE
        ticker_info = ATOM_TICKER_INFO
        profit = calculate_profit_percent(avg_position, ticker_info).quantize(TestUtils.quantizing_decimal, rounding=ROUND_UP)
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
    

if __name__ == '__main__':
    unittest.main()