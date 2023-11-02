
import unittest
from decimal import *
from strategies.utils import calculate_profit_percent
from tests.fixtures.single_trade import ATOM_SINGLE_TRADE
from tests.fixtures.ticker_info import ATOM_TICKER_INFO

MAX_PRECISION = 12

class TestUtils(unittest.TestCase):

    quantizing_decimal = Decimal(1).scaleb(-MAX_PRECISION)

    def test_calculate_profit_percent(self):
        expected_profit = Decimal(-0.09231456491391342377614447500).quantize(TestUtils.quantizing_decimal, rounding=ROUND_UP)
        avg_position = ATOM_SINGLE_TRADE
        ticker_info = ATOM_TICKER_INFO
        profit = calculate_profit_percent(avg_position, ticker_info).quantize(TestUtils.quantizing_decimal, rounding=ROUND_UP)
        self.assertEqual(profit.normalize(), expected_profit)

if __name__ == '__main__':
    unittest.main()


-0.092314564913913423776144475
-0.09231456491391341889762855999