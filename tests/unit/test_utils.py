
import unittest
from decimal import *
from utils.constants import QUANTIZING_DECIMAL
from utils.trading import calculate_profit_percent, calculate_avg_position
from tests.fixtures.single_trade import ATOM_TRADE
from tests.fixtures.multiple_trades import SOL_TRADES
from tests.fixtures.ticker_info import ATOM_TICKER_INFO

class TestUtils(unittest.TestCase):

    def test_rounding_down_shares(self):
        shares: float = 2091.2128288757876989
        rounded_shares = float(Decimal(shares).quantize(QUANTIZING_DECIMAL, rounding=ROUND_DOWN))
        expected_rounded_shares: float = 2091.212828875787
        self.assertEqual(rounded_shares, expected_rounded_shares)


    def test_calculate_profit_percent_loss(self):
        expected_profit = Decimal(-0.09231456491391342377614447500).quantize(QUANTIZING_DECIMAL, rounding=ROUND_UP)
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
    

if __name__ == '__main__':
    unittest.main()