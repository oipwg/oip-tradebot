#!/usr/bin/env python
"""Process incoming wallet transactions and write them to a database"""

from flask import Flask
import sqlite3
import sys
from authproxy import AuthServiceProxy, JSONRPCException
import json
import os

txid = sys.argv[1]
app = Flask(__name__)
app.config.from_envvar('TRADE_API_SETTINGS')

rpc_user = app.config['RPC_USER']
rpc_password = app.config['RPC_PASSWORD']
rpc_port = app.config['RPC_PORT']
currency_a = app.config['CURRENCY_A']

access = AuthServiceProxy("http://%s:%s@127.0.0.1:%s" % (rpc_user, rpc_password, rpc_port))

transactions = access.listtransactions()

con = sqlite3.connect(app.config['DATABASE'])
cur = con.cursor()
    
def add_tx_to_database(tx):
    with con:
        # First run a select to see if a receive exists
        cur.execute("SELECT txid FROM receive WHERE txid = ? LIMIT 1;" , (tx['txid'],))
        if not cur.fetchone():
        	# Add in transaction and set confirmations to 0
            cur.execute("INSERT INTO receive (currencyA, addressA, amount, txid, processed) VALUES (?, ?, ?, ?, 0);"
                , (currency_a, tx['address'], tx['amount'], tx['txid']))
            con.commit()

for tx in transactions:
    if tx['category'] == 'receive' and tx['txid'] == txid:
        add_tx_to_database(tx)

con.close()