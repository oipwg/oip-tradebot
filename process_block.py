#!/usr/bin/env python
"""Process incoming block and unprocessed receives and update the database"""

from flask import Flask
import mysql.connector
import sys
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
import json
import os

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
    
def process_transaction(tx):
    # First run a select to see if a receive has been Processed. Exit if it has been Processed.
    cursor.execute("UPDATE receive SET confirmations = %s, blockhash = %s WHERE txid = %s;", (tx['confirmations'], tx['blockhash'], tx['txid']))
    cnx.commit()

for tx in transactions:
    if tx['category'] == 'receive' and  tx['confirmations'] >= 1:
        process_transaction(tx)

cursor.close()
cnx.close()
