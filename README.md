# crypto-bot
A super simple and straight forward bot with a simple way to implement basic strategies for crypto trading.  Define a line of crypto currencies, and the strategy to BUY and SELL said crypto currencies.  The bot iterates over the list of crypto currencies and execute the appropriate trades synchronously.  The **crypto-bot** is overly optimistic by default and will never SELL at a loss even if a SELL signal is triggered (This can be overriden in the config file). 

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
wallet:accounts:read, wallet:buys:create, wallet:buys:read, wallet:notifications:read, wallet:orders:create, wallet:orders:read, wallet:sells:create, wallet:sells:read, wallet:supported-assets:read, wallet:trades:create, wallet:trades:read, wallet:transactions:read, wallet:transactions:request, wallet:transactions:send, wallet:transactions:transfer, wallet:user:read
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
The config.json is the default config file the crypto-bot will load that defines various parameters and your trading strategy.  See the following table for details on each parameter    

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
Stratgies are defined in the **strategies** field of the **config.json**




# Contributing

# Disclaimer