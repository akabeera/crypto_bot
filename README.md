# crypto-bot
A super simple and straight forward bot with a simple way to implement basic strategies via a config file for crypto trading.  Define a list of crypto currencies, and strategies to BUY and SELL said crypto currencies.  The bot iterates over the list of crypto currencies synchronously and execute the appropriate trades.  

Note: The **crypto-bot** is overly optimistic by default and will never SELL at a loss even if a SELL signal is triggered (This can be overriden in the config file). 

## Prequisites

1. Python 3.10.x  
Due to some dependency conflicts with TALib, Python 3.10.x is recommended.  I recommend [pyenv](https://github.com/pyenv/pyenv) (macOS/Linux) or [pyenv-win](https://github.com/pyenv-win/pyenv-win) (Windows) so you can easily manage different versions Python easily

2. MongoDB  
Trades are stored in MongoDB to keep track of your current positions across multiple sessions.  It's also used to calculate your overall performance.  [MongoDB community](https://www.mongodb.com/try/download/community) version will suffice but using any other tier will work as long as you have a connection string

3. TALib Core Libraries  
The crypto-bot has a dependency on the TA-Lib python library, which will automatically be installed with `pip install`.  BUT installing the python library does NOT install the necessary core TA-Lib libraries.  Please follow the directions [here to install the core TA-Lib libraries](https://github.com/TA-Lib/ta-lib-python#dependencies).  

4. Coinbase API Key  
Currently, the crypto-bot only supports coinbase exchange but more exchanges will be suppported in the future.  You'll need to create an API key through your coinbase account.  See [here](https://docs.cloud.coinbase.com/sign-in-with-coinbase/docs/api-key-authentication#generating-an-api-key) for instructions.  The below scope should be enabled AND please ensure to enable the specific Crypto Currencies you plan to run.    

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

## Running crypto-bot

### config.json
The **config.json** is the default config file the crypto-bot will load. It will defines various parameters and your trading strategy.  See the following table for details:    

### General Parameters

|  Name |  Type |  Default | Description  |
|:-:|:-:|:-:|---|
|  max_spend |  decimal |  50 | The max amount the crypto-bot will trade **per session**.  If any buy signals are triggered when the remaining balance is below the transaction amount, the BUY order will be skipped.    |
| amount_per_transaction  |  decimal | 5  |  Defines the dollar amount on a trade when a BUY signal is triggered  |
|  reinvestment_percent |  decimal | 0 |  After a SELL order, what percent of proceeds should be used for future trades. Will increase the remaining balance | 
| sleep_interval  |  decimal | 20  | Number of seconds to sleep.  The bot run **synchronously** iterating over the list of crypto currencies to trade.  Once the bot finishes iterating over the list, define the number of seconds to sleep before starting again  |
|  currency |  string |  USD | The currency to trade crypto-currency with.  Your account must be fully funded in the exchange you're using manually  |
| inter_currency_sleep_interval  |  decimal | 1  |  Number of seconds to sleep between each crypto currency |
| exchange_id  | string  | coinbase  |  Defined by [cxxt](https://github.com/ccxt/ccxt).  Currently only exhange supported is **coinbase** |
| mongodb.db_name  | string  | crypto-bot  | Name of DB in mongoDB  |
| mongodb.current_positions_collection  | string  | trades  | Name of table to store open positions  |
| mongodb.closed_positions_collection  | string  |  sell_orders |  Name of table to store closed positions, also used to calculate overall performance |
| support_currencies  | string[]  |  [] |  List of crypto currencies the bot will trade.  Use the crypto currency token (e.g. BTC, ETH, MATIC, etc) |
| blacklisted_currencies | string[]  |  [] |  List of crypto currencies to always skip |    


### Strategies  
Stratgies are defined in the **strategies** field of the **config.json**  Defining a strategy is simple, there can be multiple strategies both will evaluate each with the appropriate priority as defined in the strategy JSON.  Each strategy JSON must contain:


|  Name  |  Type |  Default |  Description |
|:-:|:-:|:-:|---|
| name  | string  |   |  The name of strategy, typically the name of the indicators such RSI, MACD.  The name MUST match the list of algready implemented indicators.  |
|  priority | number  |  0 |  Lowest numbers will always take highest priority. This defines the order in which each strategy evaluated.  You can have multiple strategies with the same priority |
| prevent_loss | boolean  | True  | Will prevent selling at a loss, even if strategy triggers a SELL signal
|  parameters |  Object |   |  Each strategy will require different parameters to perform its operations.   |    


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


# Contributing  
Anyone is free to submit pull requests to improve the usability of crypto-bot.  Few high priority features still needed are:  
1. Implementation of other common indicators/strategies
2. Configurable parameters for fetching candles for each strategy
3. Running each crypto currency asynchronously
4. Adding support for other exchanges

# Disclaimer  
Anyone is free to use the crypto-bot as they like.  But it's the user's responsibility to ensure the bot performs the transactions as expected.  It's recommended users do their own due diligence for strategies they create and to always perform necessary testing before running the crypto-bot in production. 