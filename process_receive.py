#!/usr/bin/env python
"""Processes the "receive" table and logs to "action" table. Checks x number of confirmations on receive."""

from flask import Flask
import mysql.connector
import sys
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
import json
import requests
import os
import decimal

app = Flask(__name__)
app.config.from_envvar('TRADE_API_SETTINGS')

cnx = mysql.connector.connect(user=app.config['MYSQL_USER'], password=app.config['MYSQL_PASS'], host=app.config['MYSQL_HOST'], database=app.config['MYSQL_DB'])
cursor = cnx.cursor()

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

def process_receive(receive):
    print receive[1]
    # Recieve Array Values
    # [0]: id
    # [1]: currencyA
    # [2]: addressA
    # [3]: amount
    # [4]: confirmations
    # [5]: txid
    # [6]: blockhash
    # [7]: processed

    # The core of how we process receiving of a payment
    # Process the receive and then update Processed

    bittrexLastBTCFLO, bittrexVolumeFLO  = get_bittrex_values()

    print "bittrex last: %.8f, volume: %.2f" % (bittrexLastBTCFLO, bittrexVolumeFLO)
    poloniexLastBTCFLO, poloniexVolumeFLO  = get_poloniex_values()
    print "poloniex last: %.8f, volume: %.2f" % (poloniexLastBTCFLO, poloniexVolumeFLO)

    totalVolumeFLO = bittrexVolumeFLO + poloniexVolumeFLO

    bittrexWeight =  bittrexLastBTCFLO * bittrexVolumeFLO / totalVolumeFLO
    poloniexWeight = poloniexLastBTCFLO * poloniexVolumeFLO / totalVolumeFLO
    weightedPrice = bittrexWeight + poloniexWeight

    print "weighted price: %.8f" % weightedPrice

    # Gather receiving address
    # receive[2] = addressA from Table
    cursor.execute("SELECT * FROM sendreceivemap WHERE addressA = %s;", (receive[2],))
    result = cursor.fetchone()
    # sendrecievemap Array Values
    # [0]: id
    # [1]: currencyA
    # [2]: addressA
    # [3]: currencyB
    # [4]: addressB
    addressB = result[4]
    print addressB

    # If the transaction is greater than the 0 conf amount and there have not been enough confirmations then return.
    # Recieve Array Values
    # [3]: amount
    # [4]: confirmations
    amount = receive[3]
    confirmations = receive[4]
    if amount > zeroconf and confirmations < confirms:
        return

    # Perform the send
    # Recieve Array Values
    # [3]: amount
    currencyBAmount = float(receive[3]) / weightedPrice
    txidsend = access.sendfrom("tradebot", addressB, currencyBAmount)

    # Log completion
    status = "SENT"
    action = "SENT %.8f FLO TO %s ADDRESS AT BTC RATE %.8f" % (currencyBAmount, addressB, weightedPrice)
    # Recieve Array Values
    # [5]: txid
    cursor.execute("INSERT INTO action (txidreceive, txidsend, status, action) VALUES (%s, %s, %s, %s);", (receive[5], txidsend, status, action))
    cnx.commit()

    # Update the record once it has been Processed
    print receive[1]
    # Recieve Array Values
    # [5]: txid
    cursor.execute("UPDATE receive SET processed = 1 WHERE txid = %s;", (receive[5],))
    cnx.commit()

# First run a select to see if a receive has been Processed. Exit if it has been Processed.

# Load all transactions that have not been processed
cursor.execute("SELECT * FROM receive WHERE processed = 0;")

if cursor:
    transactions = []
    for transaction in cursor:
        transactions.append(transaction)

    for receive in transactions:
        process_receive(receive)

cursor.close()
cnx.close()

