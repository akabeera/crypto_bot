# crypto-bot
A super simple and straight forward bot to develop basic strategies for crypto trading.

## Prequisites

1. Python 3.10.x  
Due to some dependency conflicts with TALib, Python 3.10.x is recommended.  I recommend [pyenv](https://github.com/pyenv/pyenv) (macOS/Linux) or [pyenv-win](https://github.com/pyenv-win/pyenv-win) (Windows) so you can easily manage different versions Python easily

2. MongoDB  
Trades are stored in MongoDB to keep track of your current positions across multiple sessions.  It's also used to calculate your overall performance.  [MongoDB community](https://www.mongodb.com/try/download/community) version will suffice but using any other tier will work as long as you have a connection string

3. TALib Core Libraries  
The crypto-bot has a dependency on the TA-Lib python library, which will automatically be installed with `pip install`.  BUT installing the python library does NOT install the necessary core TA-Lib libraries.  Please follow the directions [here to install the core TA-Lib libraries](https://github.com/TA-Lib/ta-lib-python#dependencies).  

4. Coinbase API Key  
Currently, the crypto-bot only supports coinbase exchange but more exchanges will be suppported in the future.  You'll need to create an API key through your coinbase account.  See [here](https://docs.cloud.coinbase.com/sign-in-with-coinbase/docs/api-key-authentication#generating-an-api-key) for instructions.  The below scope should be enabled and please ensure you enabled the specific Crypto Currencies you plan to run.    

``````
wallet:accounts:read, wallet:buys:create, wallet:buys:read, wallet:notifications:read, wallet:orders:create, wallet:orders:read, wallet:sells:create, wallet:sells:read, wallet:supported-assets:read, wallet:trades:create, wallet:trades:read, wallet:transactions:read, wallet:transactions:request, wallet:transactions:send, wallet:transactions:transfer, wallet:user:read
``````