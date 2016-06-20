#!/usr/bin/env python
"""Public API"""

from flask import Flask, g, request
import StringIO
import mysql.connector
import base64
import qrcode
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
import json
import os

app = Flask(__name__)
app.config.from_envvar('TRADE_API_SETTINGS')

dbconfig = {
  "user": app.config['MYSQL_USER'], 
  "password": app.config['MYSQL_PASS'], 
  "host": app.config['MYSQL_HOST'], 
  "database": app.config['MYSQL_DB']
}

cnxpool = mysql.connector.pooling.MySQLConnectionPool(pool_name = "tradebot-api-pool", pool_size = 5, **dbconfig)

def conn():
    return cnxpool.get_connection()

def make_b64_qr(address):
    qr = qrcode.QRCode()
    qr.add_data(address)
    qr.make(fit=True)
    qr_img = qr.make_image()
    bin_img = StringIO.StringIO()
    qr_img.save(bin_img, 'PNG')
    b64_data = base64.b64encode(bin_img.getvalue())
    return b64_data

def get_btc_address():
    access = AuthServiceProxy("http://%s:%s@127.0.0.1:%s" % (app.config['RPC_USER'], app.config['RPC_PASSWORD'], app.config['RPC_PORT']))
    print(access.getinfo())
    address = access.getnewaddress()
    return address

def get_flo_balance():
    access = AuthServiceProxy("http://%s:%s@127.0.0.1:%s" % (app.config['CURRENCY_B_RPC_USER'], app.config['CURRENCY_B_RPC_PASSWORD'], app.config['CURRENCY_B_RPC_PORT']))
    balance = access.getbalance()
    return balance

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route("/echo")
def echo():
    return "Echo test!"

@app.route('/depositaddress')
def depositaddress():
    con = conn()
    """Return a BTC address for deposits to a FLO address"""
    # TODO: Input validation
    # TODO: Get a new BTC deposit address
    currencyA = 'BTC'
    send_raw = False
    if 'currency' in request.args:
        currencyA = request.args['currency']
    if 'raw' in request.args:
        send_raw = True
        
    addressB = request.args['floaddress']

    # First check that an address exists
    cur = con.cursor(prepared=True)
    cur.execute("SELECT * FROM sendreceivemap WHERE addressB = %s LIMIT 1;", (addressB,))
    result = cur.fetchone()
    if not result:
        addressA = get_btc_address()
        cur.execute("INSERT INTO sendreceivemap (currencyA, addressA, currencyB, addressB) VALUES (%s, %s, 'FLO', %s);", (currencyA, addressA, addressB))
        con.commit()
    else:
        # sendrecievemap Array Values
        # [0]: id
        # [1]: currencyA
        # [2]: addressA
        # [3]: currencyB
        # [4]: addressB
        addressA = result[2]
        
    if send_raw: return addressA
    
    qr_data = make_b64_qr(addressA)
    result = '<code>{}</code><br /><img src="data:image/png;base64,{}">'.format(addressA, qr_data)

    cur.close()
    con.close()
    return result

@app.route('/flobalance')
def flobalance():
    """Return FLO balance"""
    return str(get_flo_balance())

if __name__ == "__main__":

    app.run()

