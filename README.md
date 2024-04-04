# crypto-bot
A  simple and straightforward bot with an easy way to implement basic strategies via a config file for crypto trading.  Define a list of crypto currencies, and strategies to trigger when to BUY and SELL said crypto currencies.  The bot iterates over the list of crypto currencies synchronously and execute the appropriate trades.  

Note: The **crypto-bot** is overly optimistic by default and will NEVER SELL at a loss even if a SELL signal is triggered (This can be overriden in the config file). 

## Prequisites

1. Python 3.10.x  
Due to some dependency conflicts with TALib, Python 3.10.x is recommended.  I recommend [pyenv](https://github.com/pyenv/pyenv) (macOS/Linux) or [pyenv-win](https://github.com/pyenv-win/pyenv-win) (Windows) so you can easily manage different versions Python easily

2. MongoDB  
Trades are stored in MongoDB to keep track of your current positions across multiple sessions.  It's also used to calculate your overall performance.  [MongoDB community](https://www.mongodb.com/try/download/community) version will suffice but using any other tier will work as long as you have a connection string

3. TALib Core Libraries  
The crypto-bot has a dependency on the TA-Lib python library, which will automatically be installed with `pip install`.  BUT installing the python library does NOT install the necessary dependencies for the TAL-Lib library.  The TA-Lib python library requies the core TA-Lib libraries, which you can go [here to install the core TA-Lib libraries](https://github.com/TA-Lib/ta-lib-python#dependencies).  

4. Coinbase API Key  
Currently, the crypto-bot only supports Coinbase exchange but more exchanges will be suppported in the future.  You'll need to create an API key through your coinbase account.  See [here](https://docs.cloud.coinbase.com/sign-in-with-coinbase/docs/api-key-authentication#generating-an-api-key) for instructions.  The below scope should be enabled AND please ensure to enable the specific Crypto Currencies you plan to run.    

``````
wallet:accounts:read, wallet:buys:create, wallet:buys:read,  
wallet:notifications:read, wallet:orders:create,  
wallet:orders:read, wallet:sells:create, wallet:sells:read,  
wallet:supported-assets:read, wallet:trades:create,  
wallet:trades:read, wallet:transactions:read,  
wallet:transactions:request, wallet:transactions:send,  
wallet:transactions:transfer, wallet:user:read
``````  

## Getting Started

1. [Create a virtual environment](https://docs.python.org/3/library/venv.html#creating-virtual-environments)  

```
python -m vnenv env
```

2. [Activate virtual environment](https://docs.python.org/3/library/venv.html#how-venvs-work) (chose the appropriate command corresponding to your system and environment)
```  

.\env\Scripts\activate.bat  \\Windows cmd
.\env\Scripts\Activate.ps1  \\Windows powershell

$ source env/bin/activate \\ POSIX bash/zsh
$ source env/bin/activate.fish \\ POSIX fish
$ source env/bin/activate.csh \\ POSIX csh/tcsh
$ source env/bin/Activate.ps1 \\ POSIX powershell
```

3. Install dependencies  

```
python -m pip install -r requirements.txt
```  

4. Create .env file  

```
cp .env.copy .env
```

5. Set environment variables  

```
API_KEY=<EXCHANGE_API_KEY>
API_SECRET=<EXCHANGE API_SECRET>
MONGO_CONNECTION_STRING=<MONGO_CONNECTION_STRING>
```

## Configuring crypto-bot

### config.json
The **config.json**, in your root dir, is the default config file the crypto-bot will load. It will defines various parameters and your trading strategy.  See the following table for details:    

### General Parameters
\* Required Fields 

|  Name |  Type |  Default | Description  |
|---|:-:|:-:|---|
|  * max_spend |  decimal |  -- | The max amount the crypto-bot will trade **per session**.  If any buy signals are triggered when the remaining balance is below the transaction amount, the BUY order will be skipped.    |
| * amount_per_transaction  |  decimal | --  |  Defines the dollar amount of each trade when a BUY signal is triggered  |
|  reinvestment_percent |  decimal | 0 |  After a SELL order, what percentage of proceeds should be used for future trades. Will increase the remaining balance | 
| crypto_currency_sleep_interval  |  decimal | 1  |  Number of seconds to sleep before moving on to next crypto currency on the list denoted by **supported_crypto_currencies**|
| sleep_interval  |  decimal | 20  | Number of seconds to sleep before starting back at the beginning again.  The bot runs **synchronously** over the list of crypto currencies denoted by the attribute **supported_crypto_currencies** and will sleep sleep_interval seconds before starting again.|
|  currency |  string |  USD | The currency to trade crypto-currency with.  Your account must be fully funded in the exchange you're using  |
| * exchange  | object  | --  |  JSON objects configuring exchange |
| exchange.exchange_id  | string  | coinbase  |  Defined by [cxxt](https://github.com/ccxt/ccxt).  Currently crypto-bot supports **coinbase** only |
| exchange.limit_order_period_time_limit  | number  | 4  |  Number of seconds to sleep before the crypto-bot checks status of the limit order |
| exchange.limit_order_num_periods_limit  | number  | 10  |  Controls how many periods the crypto-bot will poll the status of the limit order. If 0% is filled on the last period, the crypto-bot will cancel the limit order.  If the fill percentage increased since last comparison, the crypto-bot will reset the counter |
| * mongodb | object | -- | JSON object defining MongoDB parameters | 
| * mongodb.db_name  | string  | --  | Name of DB in mongoDB  |
| * mongodb.current_positions_collection  | string  | --  | Name of table to store open positions  |
| * mongodb.closed_positions_collection  | string  |  -- |  Name of table to store closed positions, also used in the reporting tool to calculate overall performance |
| *supported_crypto_currencies  | string[]  |  [] |  List of crypto currencies the bot will trade.  Use tickers when specifying crypto-currency (e.g. BTC, ETH, MATIC, etc) |
| blacklisted_currencies | string[]  |  [] |  List of crypto currencies to skip |    


### Strategies  
Stratgies are defined in the `strategies` attribute of **config.json.**  You define multiple indicators to develop your strategy and the indicators are evaluated based on its priority (defined by the `priority` attribute). If multiple indicators have the same priority then all must return the same action (i.e. BUY, SELL, HOLD) for the bot to perform said action.  If the bot is triggered to take action, the rest of the indicators at lower priorities are skipped. 


|  Name  |  Type |  Default |  Description |
|---|:-:|:-:|---|
| * name  | string  |  -- |  The name of the indicator.  The name MUST match the list of already implemented indicators.  See [here](https://github.com/akabeera/crypto_bot/blob/main/strategies/strategy_factory.py) for list of supported indicators  |
| * priority | number  |  -- |  Defines the order of evaluation in relation to other indicators. Lowest priorities evaluates first.  You can have multiple indicators with the same priority |
| prevent_loss | boolean  | True  | Will prevent selling at a loss, even if SELL signal is triggered
| normalization_factor | number | -- | Scale up very small numbers so calculations can be performed with Python's default precision.  Fixes the issue where too small numbers are zero-ed out  (e.g. SHIB prices)  |  
|  parameters |  Object | --  |  JSON object defining parameters necessary for the specific indicator calculation.  Each indicator have different required parameters, see below for specific indicator parameter details. |

**Indicator Parameters**

**RSI**  
The Relative Strength Index (RSI) is a momentum oscillator used in technical analysis that measures the speed and change of price movements of a security or market.  The RSI is popular among traders and analysts for identifying overbought or oversold conditions in the price of a stock or other asset, potentially indicating reversals or a weakening trend.  

|  Parameter | Type | Default |  Description |
| --- |:-:|:-:|---|
| * overbought_signal_threshold| number | -- | Triggers a SELL signal if RSI goes above this threshold |
| * oversold_signal_threshold | number |-- | Triggers a BUY signal if RSI falls below this threshold |
| timeperiod | number | 14 | The amount of most recent periods to use for RSI calculation |
| num_candles_required | number | 1 | Mininum number of periods requireed to meet thresholds to trigger a signal|  

**MACD**  
The Moving Average Convergence Divergence (MACD) is a widely used technical analysis indicator that helps to identify momentum trends and potential reversals in the price of an asset. It does this by comparing two moving averages of an asset's price, and it's defined by three key components: the fast period, slow period, and signal period  
|  Parameter | Type | Default |  Description |
| --- |:-:|:-:|---|
| fastperiod | number | 12 | Number of periods to calculate the exponential moving average (EMA) of the asset's price. This faster moving average is more sensitive to recent price movements, making it quicker to signal changes in the asset's momentum  |
| slowperiod | number | 26 | Number of periods to calculate the exponential moving average (EMA) of the asset's price. This slower moving average smooths out price data over a longer period, making it less sensitive to short-term fluctuations than the fast period. The slow period helps to provide a more stable trend indicator |
| signalperiod | number | 9 | Number of periods to calculate the exponential moving average of the MACD line.  The MACD line is result of subtracting the `slowperiod` EMA from the `fastperiod` EMA.  When the MACD line crosses above the signal line, it can indicate a bullish momentum, suggesting a potential buying opportunity. Conversely, when the MACD line crosses below the signal line, it can signal bearish momentum, indicating a potential selling opportunity   |  

**Bollinger Bands**  
Bollinger Bands are a technical analysis tool used in trading to identify potential overbought or oversold conditions in a market, as well as to gauge the volatility of a financial instrument. Bollinger Bands consist of a middle band being an N-period simple moving average (window), an upper band at K times an N-period standard deviation above the middle band, and a lower band at K times an N-period standard deviation below the middle band.
|  Parameter | Type | Default |  Description |
| --- |:-:|:-:|---|  
| window | number | 20 | Number of time periods to calculate the simple moving average for the middle band and the standard deviation used to calculate the width of the upper and lower bands. A common choice is a 20-period window, which means the middle band is the 20-period simple moving average of the price, and the standard deviation is calculated based on the same 20 periods. Adjusting the window affects the sensitivity of the bands; a shorter window makes the bands more sensitive to price movements, while a longer window makes them less sensitive. |  
| std_dev | number | 2 | A multiplier (often denoted by K in mathematical formulations) applied to the standard deviation to determine the distance of the Bollinger Bands (upper and lower) from the moving average (the middle band). A common value for this multiplier is 2, which means the upper and lower bands are set 2 standard deviations above and below the moving average, respectively. |

**ADAPTIVE_RSI** (Experimental)
Dynamically shift the overbought and oversold thresholds depending on the recent price movement and momentum
|  Parameter | Type | Default |  Description |
| --- |:-:|:-:|---|  
| default_upper_threshold | number | 70 | Initial threshold to trigger SELL signal |  
| default_lower_threshold | number | 30 | Initial threshold to trigger BUY signal |  
| volatility_factor | number | 1000 | |  
| rsi_period | number | 14 | |  
| trend_ma_period | number | 50 |  
| trend_factor | number | 500 |
    


The strategies will execute with the following heuristics:  
1. Lowest priority first  
2. If a BUY/SIGNAL signal is triggered, order is executed and lower priority strategies are skipped
3. If multiple strategies have the same priority, the ALL strategies at that priority MUST have consensus to execute a trade.  (e.g All BUY or SELL signals must be returned)  
4. If a SELL signal is triggered AND the current position is at a loss, AND **prevent_loss=TRUE** then the signal will be converted to a HOLD signal  

For example given the following **example strategy**:  

```
.
.
.
    "strategies": [
        {
            "name": "TAKE_PROFIT",
            "priority": 0,
            "parameters": {
                "threshold_percent": 10
            } 
        },
        {
            "name": "AVERAGE_DOWN",
            "priority": 1,
            "parameters": {
                "threshold_percent": 25,
                "num_times": 2
            } 
        },
        {
            "name": "BOLLINGER_BANDS",
            "priority": 2,
            "parameters": {
                "window": 20,
                "std_dev": 2
                
            }
        },
        {
            "name": "RSI",
            "priority": 2,
            "parameters": {
                "overbought_signal_threshold": 70,
                "oversold_signal_threshold": 32
            }
        },
        {
            "name": "MACD",
            "priority": 2,
            "prevent_loss": true
        }
    ]
     "support_currencies": [
        "BTC",
        "SHIB"
        .
        .
        .
     ]
    .
    .
    .

```
For EACH crypto currency defined in the **support_currencies** array the crypto bot will evaluate each strategy like the following:

1. **TAKE_PROFIT** will trigger a BUY signal if there's an open position AND profit > 10%, otherwise trigger a HOLD signal
2. If a BUY signal is triggered, skip other strategies and move on to the next crypto currency on the list, otherwise go to #3
3. **AVERAGE_DOWN** will trigger a BUY signal if there's an open position and profit <= -25%, otherwise trigger a HOLD
4. If BUY signal is triggered, skip other strategies and move on to the next crypto currency on the list, otherwise go to #5
5. **RSI**, **MACD**, **BOLLINGER_BANDS**  all have same priorty so ALL three must trigger BUY/SELL, otherwise is NOOP signal is triggered
6. If all three above triggers BUY/SELL then execute the appropriate order and move on to the next crypto currency  

### Config Overrides

# Admin Utilities

# Reporting Dashboard

# Contributing  
Anyone is free to submit pull requests to improve the usability of crypto-bot.  Few high priority features still needed are:  
1. Implementation of other common indicators/strategies
2. Configurable parameters for fetching candles for each strategy
3. Running each crypto currency asynchronously
4. Adding support for other exchanges

# Disclaimer  
Anyone is free to use the crypto-bot as they like.  But it's the user's responsibility to ensure the bot performs the transactions as expected.  It's recommended users do their own due diligence when creating their strategies.  It's important to always perform necessary testing before running the crypto-bot in production.  There's no guarantee the bot is bug free, so it's important to do comprehensive testing before letting the bot execute real trades.  Users can use the dry-run flat to help in testing and confirming expected behavior.    