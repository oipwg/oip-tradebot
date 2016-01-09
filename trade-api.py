#!/usr/bin/env python
"""Public API"""

from flask import Flask, g, request
import StringIO
import sqlite3
import base64
import qrcode
from jsonrpc import ServiceProxy
import json
import os

app = Flask(__name__)
app.config.from_envvar('TRADE_API_SETTINGS')

def connect_to_database():
    return sqlite3.connect(app.config['DATABASE'])

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = connect_to_database()
    return db

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
    access = ServiceProxy("http://%s:%s@127.0.0.1:%s" % (app.config['RPC_USER'], app.config['RPC_PASSWORD'], app.config['RPC_PORT']))
    address = access.getnewaddress()
    return address

def get_flo_balance():
    access = ServiceProxy("http://%s:%s@127.0.0.1:%s" % (app.config['CURRENCY_B_RPC_USER'], app.config['CURRENCY_B_RPC_PASSWORD'], app.config['CURRENCY_B_RPC_PORT']))
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
    """Return a BTC address for deposits to a FLO address"""
    # TODO: Input validation
    # TODO: Get a new BTC deposit address
    currencyA = 'BTC'
    send_raw = False
    if 'currency' in request.args:
        currencyA = request.args['currency']
    if 'raw' in request.args['raw']:
        send_raw = True
        
    addressB = request.args['floaddress']

    # First check that an address exists
    get_db().row_factory=sqlite3.Row
    cur = get_db().cursor()
    cur.execute("SELECT * FROM sendreceivemap WHERE addressB = ? LIMIT 1;", (addressB,))
    result = cur.fetchone()
    if not result:
        addressA = get_btc_address()
        #cur.execute("update sendreceivemap set addressB = ? where addressB = "" limit 1;", (addressB,))
        cur.execute("INSERT INTO sendreceivemap (currencyA, addressA, currencyB, addressB) VALUES (?, ?, 'FLO', ?);"
                , (currencyA, addressA, addressB))
        get_db().commit()
    else:
        addressA = result["addressA"]
        
    qr_data = make_b64_qr(addressA)
    result = '<code>{}</code><br /><img src="data:image/png;base64,{}">'.format(addressA, qr_data)
    
    if send_raw: return addressA
    return result

@app.route('/flobalance')
def flobalance():
    """Return FLO balance"""
    return str(get_flo_balance())

if __name__ == "__main__":

    app.run()

