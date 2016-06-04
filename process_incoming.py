#!/usr/bin/env python
"""Process incoming wallet transactions and write them to a database"""

from flask import Flask
import mysql.connector
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

cnx = mysql.connector.connect(user=app.config['MYSQL_USER'], password=app.config['MYSQL_PASS'], host=app.config['MYSQL_HOST'], database=app.config['MYSQL_DB'])
cursor = cnx.cursor()
    
def add_tx_to_database(tx):
    # First run a select to see if a receive exists
    cursor.execute("SELECT txid FROM receive WHERE txid = %s LIMIT 1;" , (tx['txid'],))
    if not cursor.fetchone():
    	# Add in transaction and set confirmations to 0
        cursor.execute("INSERT INTO receive (currencyA, addressA, amount, txid, processed) VALUES (%s, %s, %s, %s, 0);", (currency_a, tx['address'], tx['amount'], tx['txid']))
        cnx.commit()

for tx in transactions:
    if tx['category'] == 'receive' and tx['txid'] == txid:
        add_tx_to_database(tx)

cursor.close()
cnx.close()