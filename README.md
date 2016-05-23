# Requirements

flask
pillow

# Running

Running the API

```
$ export TRADE_API_SETTINGS=/path/to/trade_api_settings.cfg  
$ python trade-api.py
 * Running on http://127.0.0.1:5000/
```

# How it works

### Code Flow
1. User creates request to purchase some FLO and includes their FLO address in a request: `http://127.0.0.1:5000/depositaddress?floaddress=FBWWMomgvKFi27ihZzLXUyF3QeS6F5iQcK`
2. The API receives the call, first we check to see if that FLO address already has a Bitcoin address, if it does not it creates a new Bitcoin address to receive at, this is added to the database along with the Florincoin address.
3. A QR Code and the Bitcoin address is returned to the user in the browser. If they add `?raw` to the request then only a Bitcoin address will be returned.
4. The user sends Bitcoin to the displayed address.
5. `process_incoming.py` is run by bitcoind. Once bitcoind sees that there is a new transaction on the blockchain it calls this script with the txid as a paramater. This is added to the database with 0 confirmations.
6. `process_block.py` is run by bitcoind. It checks for new confirmations and updates the database once there is at least one confirmation.
7. `process_receive.py` is run by the crontab. Once it hits the amount of required confirmations (set in `trade_api_settings.cfg` under `NUMBER_OF_CONFIRMATIONS_REQUIRED`) or is below the zero confirmation limit (set in `trade_api_settings.cfg` under `ZERO_CONF_MAX_BTC`) it sends the Florincoin to the user then sets the transaction as processed in the database.

# Config

The example configuration can be found in `trade_api_settings.cfg.example`. It is outlined here as well.

```
# BTC
RPC_USER = 'bitcoinrpc'
RPC_PASSWORD = 'PASSWORD GOES HERE'
RPC_PORT = 8332
CURRENCY_A = 'BTC'

#FLO
CURRENCY_B_RPC_USER = 'florincoinrpc'
CURRENCY_B_RPC_PASSWORD = 'PASSWORD GOES HERE'
CURRENCY_B_RPC_PORT = 18322
CURRENCY_B = 'FLO'

NUMBER_OF_CONFIRMATIONS_REQUIRED = 1
ZERO_CONF_MAX_BTC = 0.001
DATABASE = '/path/to/alexandria_payment.db'
DEBUG = False
```

If you would like to allow zero confirmation sending, set `ZERO_CONF_MAX_BTC` to the maximum amount you want a zero confirmation send to happen. This value is in BTC.

NOTE: We highly suggest you do NOT set the number of confirmations to 0 as this very dangerous due to transaction malleability which WILL cause a double spend.

## Cron/Bitcoin Tasks
### Cron
You need to run `process_receive.py` via the cron every one to five minutes. We suggest that you run it every minute and use the following cron job created for you below.

```
*/1 * * * * cd /path/to/tradebot && python process_receive.py
```

### Bitcoin
You need to add two lines to your `bitcoin.conf` file in order to get it running. These lines make sure that the incoming transactions and blocks are processed instantly. Make sure to also add any RPC information to the config while you are here.

```
walletnotify=/path/to/tradebot/process_incoming.py %s
blocknotify=/path/to/tradebot/process_block.py %s
```

`walletnotify` runs when an incoming wallet transaction is received on the Bitcoin network.  The argument passed through is the transaction ID.

`blocknotify` runs when a new block is received on the Bitcoin network.  The argument passed through is the block hash.