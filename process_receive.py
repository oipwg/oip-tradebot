#!/usr/bin/env python
"""Processes the "receive" table and logs to "action" table. Checks x number of confirmations on receive."""

from flask import Flask
import sqlite3
import sys
from authproxy import AuthServiceProxy, JSONRPCException
import json
import requests
import os

app = Flask(__name__)
app.config.from_envvar('TRADE_API_SETTINGS')

con = sqlite3.connect(app.config['DATABASE'])
con.row_factory = sqlite3.Row
cur = con.cursor()

rpc_user = app.config['RPC_USER']
rpc_password = app.config['RPC_PASSWORD']
rpc_port = app.config['RPC_PORT']
currency_a = app.config['CURRENCY_A']

# The number of confirmations before sending the transaction.
confirms = app.config['NUMBER_OF_CONFIRMATIONS_REQUIRED']
zeroconf = app.config['ZERO_CONF_MAX_BTC']

access = AuthServiceProxy("http://%s:%s@127.0.0.1:%s" % (rpc_user, rpc_password, rpc_port))

def get_bittrex_values():
    url = 'https://bittrex.com/api/v1.1/public/getmarketsummary?market=btc-flo'
    try:
        r = requests.get(url)
    except requests.exceptions.ConnectionError:
        print "Unable to connect to Bittrex API ;_;"
    m = r.json()['result'][0]
    
    bittrexLastBTCFLO = m['Last']
    bittrexVolumeFLO = m['Volume']
    return bittrexLastBTCFLO, bittrexVolumeFLO

def get_poloniex_values():
    url = 'https://poloniex.com/public?command=returnTradeHistory&currencyPair=BTC_FLO'
    try:
        r = requests.get(url)
    except requests.exceptions.ConnectionError:
        print "Unable to connect to Poloniex API ;_;"
    m = r.json()
    poloniexLastBTCFLO = m[0]['rate']

    url = 'https://poloniex.com/public?command=return24hVolume'
    try:
        r = requests.get(url)
    except requests.exceptions.ConnectionError:
        print "Unable to connect to Poloniex API ;_;"
    m = r.json()
    poloniexVolumeFLO = m['BTC_FLO']['FLO']

    return float(poloniexLastBTCFLO), float(poloniexVolumeFLO)


def get_cryptsy_values():
    url = 'http://pubapi.cryptsy.com/api.php?method=singlemarketdata&marketid=3'
    try:
        r = requests.get(url)
    except requests.exceptions.ConnectionError:
        print "Unable to connect to Cryptsy API ;_;"
    m = r.json()['return']['markets']['LTC']
    cryptsyLastBTCLTC = m['lasttradeprice']

    url = 'http://pubapi.cryptsy.com/api.php?method=singlemarketdata&marketid=61'
    try:
        r = requests.get(url)
    except requests.exceptions.ConnectionError:
        print "Unable to connect to Cryptsy API ;_;"
    m = r.json()['return']['markets']['FLO']
    cryptsyLastLTCFLO = m['lasttradeprice']
    cryptsyVolumeFLO = m['volume']

    return float(cryptsyLastBTCLTC), float(cryptsyLastLTCFLO), float(cryptsyVolumeFLO)

def process_receive(receive):
    # The core of how we process receiving of a payment
    # Process the receive and then update Processed

    cryptsyLastBTCLTC, cryptsyLastLTCFLO, cryptsyVolumeFLO  = get_cryptsy_values()
    print "cryptsy last BTC/LTC: %.8f, last: %.8f, volume: %.2f" % (cryptsyLastBTCLTC, cryptsyLastLTCFLO, cryptsyVolumeFLO)

    bittrexLastBTCFLO, bittrexVolumeFLO  = get_bittrex_values()

    print "bittrex last: %.8f, volume: %.2f" % (bittrexLastBTCFLO, bittrexVolumeFLO)
    poloniexLastBTCFLO, poloniexVolumeFLO  = get_poloniex_values()
    print "poloniex last: %.8f, volume: %.2f" % (poloniexLastBTCFLO, poloniexVolumeFLO)

    totalVolumeFLO = cryptsyVolumeFLO + bittrexVolumeFLO + poloniexVolumeFLO

    cryptsyWeight = cryptsyLastBTCLTC * cryptsyLastLTCFLO * cryptsyVolumeFLO / totalVolumeFLO
    bittrexWeight =  bittrexLastBTCFLO * bittrexVolumeFLO / totalVolumeFLO
    poloniexWeight = poloniexLastBTCFLO * poloniexVolumeFLO / totalVolumeFLO
    weightedPrice = cryptsyWeight + bittrexWeight + poloniexWeight

    print "weighted price: %.8f" % weightedPrice

    # Gather receiving address
    cur.execute("SELECT * FROM sendreceivemap WHERE addressA = ?", (receive['addressA'],))
    result = cur.fetchone()
    addressB = result["addressB"]

    # If the transaction is greater than the 0 conf amount and there have not been enough confirmations then return.
    if amount > zeroconf and receive['confirmations'] < confirms:
        return

    # Perform the send
    currencyBAmount = receive['amount'] / weightedPrice
    txidsend = access.sendtoaddress(addressB, currencyBAmount)

    # Log completion
    status = "SENT"
    action = "SENT %.8f FLO TO %s ADDRESS AT BTC RATE %.8f" % (currencyBAmount, addressB, weightedPrice)
    cur.execute("INSERT INTO action (txidreceive, txidsend, status, action) VALUES (?, ?, ?, ?);"
        , (receive['txid'], txidsend, status, action))
    con.commit()

    # Update the record once it has been Processed
    cur.execute("UPDATE receive SET processed = 1 WHERE txid = ?;", (receive['txid'],))
    con.commit()

# First run a select to see if a receive has been Processed. Exit if it has been Processed.
with con:
    # Load all transactions that have not been processed
    cur.execute("SELECT * FROM receive WHERE processed = 0;")
    results = cur.fetchall()

if results:
    for receive in results:
        process_receive(receive)

con.close()

