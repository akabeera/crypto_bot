import unittest
import json

from utils.strategies import init_strategies, init_strategies_overrides

class TestStrategiesInit(unittest.TestCase):
    def test_invalid_config(self):
        CONFIG_FILE = "./tests/fixtures/configs/strategies_config_invalid.json"
        config = {}

        with open(CONFIG_FILE) as f:
            config = json.load(f)
        
        strategies = init_strategies(config)
        expected_strategies = dict()
        self.assertEqual(strategies, expected_strategies)

    def test_valid_config(self):
        CONFIG_FILE = "./tests/fixtures/configs/strategies_config.json"
        config = {}

        with open(CONFIG_FILE) as f:
            config = json.load(f)

        strategies = init_strategies(config)

        expected_keys = [1,2]
        expected_priority_1_strategy_name = "AVERAGE_DOWN"
        expected_priority_2_strategy_names = ["BOLLINGER_BANDS", "RSI", "MACD"]

        self.assertEqual(list(strategies.keys()), expected_keys)
        self.assertEqual(strategies[1][0].name, expected_priority_1_strategy_name)

        priority_2_strategy_names = []
        for strategy in strategies[2]:
            priority_2_strategy_names.append(strategy.name)

        self.assertEqual(set(priority_2_strategy_names), set(expected_priority_2_strategy_names))

    def test_valid_config_with_enabled_flag(self):
        CONFIG_FILE = "./tests/fixtures/configs/strategies_config_with_enabled_flag.json"
        config = {}

        with open(CONFIG_FILE) as f:
            config = json.load(f)

        strategies = init_strategies(config)
        expected_keys = [2]

        self.assertEqual(list(strategies.keys()), expected_keys)

        expected_strategy_names = ["RSI", "MACD"]
        strategy_names = []
        for strategy in strategies[2]:
            strategy_names.append(strategy.name)
        self.assertEqual(set(strategy_names), set(expected_strategy_names))

    def test_valid_config_with_empty_overrides(self):
        CONFIG_FILE = "./tests/fixtures/configs/strategies_overrides_empty.json"
        config = {}

        with open(CONFIG_FILE) as f:
            config = json.load(f)

        strategies_overrides = init_strategies_overrides(config)
        self.assertEqual(len(strategies_overrides), 0)
        
    def test_valid_config_with_valid_overrides(self):
        CONFIG_FILE = "./tests/fixtures/configs/strategies_overrides_valid.json"
        config = {}

        with open(CONFIG_FILE) as f:
            config = json.load(f)

        strategies_overrides = init_strategies_overrides(config)
        expected_num_strategies_overrides = 3
        self.assertEqual(len(strategies_overrides), expected_num_strategies_overrides)

        expected_keys = ["SHIB/USD", "WCFG/USD", "OXT/USD"]
        self.assertEqual(set(strategies_overrides.keys()), set(expected_keys))


if __name__ == '__main__':
    unittest.main()