#!/usr/bin/env python
"""Public API"""

from datetime import date
from flask import Flask, g, request
import StringIO
import mysql.connector.pooling
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
    balance = access.getbalance("tradebot")
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
    
    cur.close()
    con.close()
    
    if send_raw: return addressA
    
    qr_data = make_b64_qr(addressA)
    result = '<code>{}</code><br /><img src="data:image/png;base64,{}">'.format(addressA, qr_data)
    
    return result

@app.route('/flobalance')
def flobalance():
    """Return FLO balance"""
    return str(get_flo_balance())

@app.route('/faucet', methods=['POST'])
def faucet():
    """Send 1 FLO to requested address"""
    if 'X-Forwarded-For' in request.headers:
        remote_addr = request.headers.getlist("X-Forwarded-For")[0].rpartition(' ')[-1]
    else:
        remote_addr = request.remote_addr or 'untrackable'

    flo_address = request.form.get("flo_address")

    print flo_address

    if flo_address is None:
        return '{"success": false, "message": "No address provided"}'

    con = conn()
    dt = date.today()

    access = AuthServiceProxy("http://%s:%s@127.0.0.1:%s" % (app.config['CURRENCY_B_RPC_USER'], app.config['CURRENCY_B_RPC_PASSWORD'], app.config['CURRENCY_B_RPC_PORT']))

    # Check if they've already requested today
    cur = con.cursor(prepared=True)
    cur.execute("SELECT * FROM faucet WHERE flo_address = %s AND date_today = %s LIMIT 1;", (flo_address, dt))
    result = cur.fetchone()
    if not result:
        cur.execute("SELECT * FROM faucet WHERE remote_addr = %s AND date_today = %s LIMIT 1;", (remote_addr, dt))
        result = cur.fetchone()
        if not result:
            # Send some FLO
            try:
                txidsend = access.sendfrom("faucet", flo_address, 1)
                result = '{"success": true, "txid": "%s"}' % txidsend
                cur.execute("INSERT INTO faucet (flo_address, remote_addr, date_today, txid_send) VALUES (%s, %s, %s, %s);", (flo_address, remote_addr, dt, txidsend))
                con.commit()
            except JSONRPCException:
                print 'Error sending FLO from Faucet'
                result = '{"success": false, "message": "No FLO Left in Faucet"}'
        else:
            result = '{"success": false, "message": "This IP has already recieved money today!"}'
    else:
        # Already sent some FLO today
        result = '{"success": false, "message": "This address has already recieved money today!"}'

    cur.close()
    con.close()

    return result

if __name__ == "__main__":

    app.run("0.0.0.0")

