import collections
import os
import sys
from flask import Flask, render_template, flash, redirect, url_for, session, request, logging, jsonify, request
from flask_cors import CORS
import websocket, json
import pandas as pd
import numpy as np
import pandas_ta as ta
from binance.client import Client
from binance.enums import *
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import datetime
import requests
import threading
import jwt 


cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)

db = firestore.client()
ref = db.collection(u'init').document(u'current')

SOCKET = "wss://stream.binance.com:9443/ws/ethusdt@kline_1h"

# TRADE_SYMBOL = 'ETHUPUSDT'
risk = 0.03
atr_multiple = 3
# activation = True
coin = "ETH"
LATEST_BOUGHT = 0
SL = 0
sticks = 0
in_position = False
position = "None"

is_online = False
SL_active = False

position = None

global SOCKET_THREAD
global INIT_THREAD

global t1

#define constants - periods
API_KEY = os.environ.get('API_KEY', None)
API_SECRET = os.environ.get('API_SECRET', None)
#initialize
client = Client(API_KEY, API_SECRET)


# client.API_URL = "https://testnet.binance.vision/api"

tracker = {
    "ETH": {
        "close":[],
        "open":[],
        "high":[],
        "low":[],
        "hl2":[]
    }
}

def Init_candle(n):
    global ref, LATEST_BOUGHT, SL, sticks, in_position, position, coin
    n = n*-1
    klines = client.get_historical_klines("ETHUSDT", Client.KLINE_INTERVAL_1HOUR, "6 day ago UTC")
    useful = klines[n:]
    useful.pop()
    # print(useful)
    for i in useful:
        #i is an array
        open_price = i[1]
        high_price = i[2]
        low_price = i[3]
        close_price = i[4]
        tracker[coin]['close'].append(float(close_price))
        tracker[coin]['high'].append(float(high_price))
        tracker[coin]['low'].append(float(low_price))
        tracker[coin]['open'].append(float(open_price))
        tracker[coin]['hl2'].append((float(high_price)+float(low_price))/2)
    # for i in range(-14:)
    # print(tracker)
    initial = ref.get().to_dict()
    print("TRACKER INIT ,", len(tracker[coin]["close"]))
    print("CURRENTLY AT ,", tracker[coin]["close"][-1])
    print(initial)
    # print(initial)
    LATEST_BOUGHT = float(initial["LATEST_BOUGHT"])
    sticks = int(initial["sticks"])
    SL = float(initial["SL"])
    in_position = initial["in_position"]
    position = initial["position"]

def CalcSize(atr, price):
    global LOT,ref
    USDT = client.get_asset_balance(asset='USDT')
    current_balance = float(USDT['free'])
    print("USTD FREE {}".format(current_balance))
    
    
    delta = (atr*atr_multiple)/price
    risk_amount = risk*current_balance
    size = round(risk_amount/delta,2)

    if size > current_balance:
        print("SIZE(1): {}, ATR {}, BALANCE: {}".format(0.9*current_balance, atr*atr_multiple,current_balance))
        return round((0.9*current_balance)/3.5,4)
    print("SIZE(2): {}, ATR {}, BALANCE: {}".format(size,atr*atr_multiple,current_balance))
    # lot_size = round(size,6)
    # lot_size = current_value*0.5
    return round(size/3.5,4)

def Enter_long(adx,red,yellow,green,brown,blue,pink,close,position):
    if position == False and close > pink:
        if adx > 15:
            if red > yellow and yellow > green and close > green:
                return True
            else:
                return False
        else:
            return False
    else:
        return False

def Enter_short(adx,red,yellow,green,brown,blue,pink,close,position):
    if position == False and close < pink:
        if adx > 15:
            if red < yellow and yellow < green and close < green:
                return True
            else:
                return False
        else:
            return False
    else:
        return False

def Exit_long(adx,red,yellow,green,brown,blue,pink,close,position,status):
    if status == 'long' and position == True:
        if adx >= 0 and adx < 25 and blue < pink:
            # print("blue")
            print(f"ADX {adx}, PRICE {close}, COLOR-blue {blue}")
            return True
        elif adx >= 25 and adx < 30 and brown < blue:
            # print("green")
            print(f"ADX {adx}, PRICE {close}, COLOR-brown {brown}")
            return True
        elif adx >= 30 and adx < 45 and green < brown:
            # print("green")
            print(f"ADX {adx}, PRICE {close}, COLOR-green {green}")
            return True
        elif adx >= 45 and yellow < green:
            print(f"ADX {adx}, PRICE {close}, COLOR-green {yellow}")
            return True
        else:
            return False
    else:
        return False

def Exit_short(adx,red,yellow,green,brown,blue,pink,close,position,status):
    if status == 'short' and position == True:
        if adx >= 0 and adx < 25 and blue > pink:
            # print("blue")
            print(f"ADX {adx}, PRICE {close}, COLOR-blue {blue}")
            return True
        elif adx >= 25 and adx < 30 and brown > blue:
            # print("green")
            print(f"ADX {adx}, PRICE {close}, COLOR-brown {brown}")
            return True
        elif adx >= 30 and adx < 45 and green > brown:
            # print("green")
            print(f"ADX {adx}, PRICE {close}, COLOR-green {green}")
            return True
        elif adx >= 45 and yellow > green:
            print(f"ADX {adx}, PRICE {close}, COLOR-green {yellow}")
            return True
        else:
            return False
    else:
        return False


def New_Kline(n,c,o,h,l,coin):
    tracker[coin]["close"].append(round(float(c),2))
    tracker[coin]["open"].append(round(float(o),2))
    tracker[coin]["high"].append(round(float(h),2))
    tracker[coin]["low"].append(round(float(l),2))
    tracker[coin]['hl2'].append( round((float(h)+float(l))/2,2) )

    #cleaning process prevent memory flood
    if len(tracker[coin]["close"]) > n:
        tracker[coin]["close"].pop(0)
    if len(tracker[coin]["open"]) > n:
        tracker[coin]["open"].pop(0)
    if len(tracker[coin]["high"]) > n:
        tracker[coin]["high"].pop(0)
    if len(tracker[coin]["low"]) > n:
        tracker[coin]["low"].pop(0)
    if len(tracker[coin]["hl2"]) > n:
        tracker[coin]["hl2"].pop(0)
    return


def Order(side,ATR,status,price,pairup,pairdown,symbolup,symboldown):
    global in_position, SL, LATEST_BOUGHT, db, position
    #geting currnet price of ETHUP and set equal to price
    klines_up = client.get_historical_klines(pairup, Client.KLINE_INTERVAL_1MINUTE, "10 minutes ago UTC")
    klines_down = client.get_historical_klines(pairdown, Client.KLINE_INTERVAL_1MINUTE, "10 minutes ago UTC")

    up_price = float(klines_up[-1][4])
    down_price = float(klines_down[-1][4])

    print("ordering..")
    try:
        print("sending order")
        if status == 'open_long' and in_position == False:
            #check if any orders
            print("buying up...")
            open_orders = client.get_open_orders(symbol=pairup)
            if open_orders == []:
                quantity = round(CalcSize(ATR,price)/up_price,3)
                # comission = round(quantity*0.001,3)
                comission = 0.001
                actual_size = round((quantity-(quantity*comission))- 0.02,2)
                print("BUY QUANTITY {}".format(actual_size))
                LATEST_BOUGHT = price
                ref.update({"LATEST_BOUGHT": price})
                SL = round(price-(ATR*atr_multiple),5)
                print("SL : {}".format(SL))
                ref.update({"SL": SL})
                order = client.order_market_buy(symbol=pairup, quantity=actual_size)
                in_position = True
                ref.update({"in_position": True})
                
                position = "long"
                ref.update({"position": "long"})

            else:
                print("STILL HAS OPEN ORDERS", open_orders)


        elif status == 'close_long' and in_position == True and position == 'long':
            #check if any open orders
            print("selling up...")
            open_orders = client.get_open_orders(symbol=pairup)
            if open_orders == []:
                ETH = client.get_asset_balance(asset=symbolup)
                quantity = round(float(ETH['free'])- 0.01,2)
                print("SELL QUANTITY {}".format(quantity))
                order = client.order_market_sell(symbol=pairup, quantity=quantity)
                in_position = False
                ref.update({"in_position": False})

                position = "None"
                ref.update({"position": "None"})
            else:
                print("STILL HAS OPEN ORDERS:",open_orders)

        elif status == "open_short" and in_position == False:
            print(pairdown)
            print("buying down...")
            open_orders = client.get_open_orders(symbol='ETHDOWNUSDT')
            print(open_orders)
            if open_orders == []:
                quantity = round(CalcSize(ATR,price)/down_price,3)
                # comission = round(quantity*0.001,3)
                comission = 0.001
                actual_size = round(quantity-(quantity*comission)- 0.02,2)
                print("BUY QUANTITY {}".format(actual_size))
                LATEST_BOUGHT = price
                ref.update({"LATEST_BOUGHT": price})
                SL = round(price+(ATR*atr_multiple),5)
                print("SL : {}".format(SL))
                ref.update({"SL": SL})
                order = client.order_market_buy(symbol=pairdown, quantity=actual_size)
                in_position = True
                ref.update({"in_position": True})

                position = "short"
                ref.update({"position": "short"})
            else:
                print("STILL HAS OPEN ORDERS", open_orders)
        
        elif status == 'close_short' and in_position == True and position == 'short':
            #check if any open orders
            print("selling down...")
            open_orders = client.get_open_orders(symbol=pairdown)
            if open_orders == []:
                ETH = client.get_asset_balance(asset=symboldown)
                quantity = round((float(ETH['free']) - 0.01),2)
                print("SELL QUANTITY {}".format(quantity))
                order = client.order_market_sell(symbol=pairdown, quantity=quantity)
                in_position = False
                ref.update({"in_position": False})

                position = "None"
                ref.update({"position": "None"})
            else:
                print("STILL HAS OPEN ORDERS:",open_orders)


        print(order)
        # data = json.dumps(order)
        try:
            db.collection('trades').add(order)
            print("TRADE STORED IN FIREBASE!")
            return True
        except Exception as firebase_e:
            print("FIREBASE ERROR: - {}".format(firebase_e))
        return False
    except Exception as e:
        print("BINANCE ERROR - {}".format(e))

        # in_position = False
        # ref.update({"in_position": False})

        return False

def on_open(ws):
    global is_online
    is_online = True
    print(is_online)
    print('opened connection')

def on_close(ws):
    global is_online
    is_online = False
    print('closed connection')

def on_message(ws, message):
    global in_position, tracker, sticks, SL, LATEST_BOUGHT, SL_active, position

    json_message = json.loads(message)
    # pprint.pprint(json_message)
    #,coin,pairup,pairdown,symbolup,symboldown
    coin = json_message['s'].split('USDT')[0]
    symbolup = coin + 'UP'
    symboldown = coin + 'DOWN'
    pairup = coin + 'UPUSDT'
    pairdown = coin + 'DOWNUSDT'
    candle = json_message['k']
    is_candle_closed = candle['x']

    close_price = candle['c']
    open_price = candle['o']
    high_price = candle['h']
    low_price = candle['l']
    # print(in_position)
    if position == "long" and float(close_price) < SL and in_position == True and SL_active == False:
        try:
            SL_active = True
            print("STOP LOSS [ACTIVATE]: SL {}, PRICE {}".format(SL,float(close_price)))
            print("SELLING UP...")
            open_orders = client.get_open_orders(symbol=pairup)
            if open_orders == []:
                ETH = client.get_asset_balance(asset=symbolup)
                quantity = round(float(ETH['free'])- 0.01,2)
                sl_order = client.order_market_sell(symbol=pairup, quantity=quantity)

                SL = 0
                ref.update({"SL": 0})

                in_position = False
                ref.update({"in_position": False})

                position = "None"
                ref.update({"position": "None"})

                print("STOP LOSS [DEACTIVATE]")
                SL_active = False
            else:
                print("STILL HAS OPEN ORDERS:",open_orders)
        except Exception as e:
            print("ORDERING AT STOPLOSS ERROR - {}".format(e))
    
    elif position == "short" and float(close_price) > SL and in_position == True and SL_active == False:
        try:
            SL_active = True
            print("STOP LOSS [ACTIVATE]: SL {}, PRICE {}".format(SL,float(close_price)))
            print("SELLING DOWN...")
            open_orders = client.get_open_orders(symbol=pairdown)
            if open_orders == []:
                ETH = client.get_asset_balance(asset=symboldown)
                quantity = round((float(ETH['free']) - 0.01),2)
                sl_order = client.order_market_sell(symbol=pairdown, quantity=quantity)

                SL = 0
                ref.update({"SL": 0})

                in_position = False
                ref.update({"in_position": False})

                position = "None"
                ref.update({"position": "None"})

                print("STOP LOSS [DEACTIVATE]")
                SL_active = False
            else:
                print("STILL HAS OPEN ORDERS:",open_orders)
        except Exception as e:
            print("ORDERING AT STOPLOSS ERROR - {}".format(e))

    if is_candle_closed:
        print(coin)
        print("TRACKER LENGTH: ", len(tracker[coin]['close']))
        sticks += 1
        ref.update({"sticks": sticks})
        print("Candle stick: {}".format(sticks))

        print("Position Status: {}".format(in_position))

        print("candle closed at {}".format(close_price))

        New_Kline(120,float(close_price),float(open_price),float(high_price),float(low_price),coin)
        # print(tracker)
        print(len(tracker[coin]["close"])-1)
        if len(tracker[coin]['close']) == 120:
            print("Calc")
            try:
                df = pd.DataFrame({"open": tracker[coin]["open"], "close": tracker[coin]["close"], "high": tracker[coin]["high"], "low": tracker[coin]["low"], "hl2": tracker[coin]["hl2"]},columns=["open","close","high","low","hl2"])
                
                red = ta.ema(df['hl2'], length=3, offset=2, append=False)
                yellow = ta.ema(df['hl2'], length=5,  offset=3, append=False)
                green = ta.ema(df['hl2'], length=8,  offset=5, append=False)
                brown = ta.ema(df['hl2'], length=13,  offset=8, append=False)
                blue = ta.ema(df['hl2'], length=21,  offset=13, append=False)
                pink = ta.ema(df['hl2'], length=34,  offset=21, append=False)
                atr = ta.atr(df['high'],df['low'],df['close'],length=14, mamode=None, drift=None, offset=None, append=False)
                adx = ta.adx(df['high'],df['low'],df['close'],length=14, lensig=None, scalar=None, offset=None)
                
                red_val = red[len(tracker[coin]["close"])-1]
                yellow_val = yellow[len(tracker[coin]["close"])-1]
                green_val = green[len(tracker[coin]["close"])-1]
                brown_val = brown[len(tracker[coin]["close"])-1]
                blue_val = blue[len(tracker[coin]["close"])-1]
                pink_val = pink[len(tracker[coin]["close"])-1]
                atr_val = atr[len(tracker[coin]["close"])-1]

                adx_arr = adx['ADX_14']
                adx_val = adx_arr[len(tracker[coin]["close"])-1]


                # print("AROONUP {}, AROONDOWN {}, BLUE {}, RED {}, GREEN {}, RSI {}, LATEST_BOUGHT {}, EMA100 {} , ATR {}, STOP_LOSS {}".format(aroonup_val,aroondown_val,blue_val,red_val,green_val,rsi_val,LATEST_BOUGHT,ema_val,atr_val,SL))
                print("red {}, yellow {}, green {}, brown {}, blue {}, pink {}, LATEST_BOUGHT {}, ADX{}, ATR {}, STOP_LOSS {}".format(red_val, yellow_val, green_val, brown_val, blue_val, pink_val, LATEST_BOUGHT, adx_val,atr_val,SL))
            except Exception as e:
                print("EXCEPTION" + e)

            if  Enter_long(adx_val,red_val,yellow_val,green_val,brown_val,blue_val,pink_val,tracker[coin]['close'][-1],in_position) == True and in_position == False:
                print("OPEN LONG")
                # side,ATR,status,price,pairup,pairdown,symbolup,symboldown
                order_succeed = Order(SIDE_BUY,atr_val,'open_long',tracker[coin]['close'][-1],pairup,pairdown,symbolup,symboldown)
                if order_succeed:
                    in_position = True
                    ref.update({"in_position": True})

            elif Exit_long(adx_val,red_val,yellow_val,green_val,brown_val,blue_val,pink_val,tracker[coin]['close'][-1],in_position,position) == True and in_position == True and position == 'long':
                print("CLOSE LONG")

                order_succeed = Order(SIDE_SELL,atr_val,'close_long',tracker[coin]['close'][-1],pairup,pairdown,symbolup,symboldown)
                if order_succeed:
                    SL = 0
                    ref.update({"SL": 0})
                    in_position = False
                    ref.update({"in_position": False})
                    
            elif Enter_short(adx_val,red_val,yellow_val,green_val,brown_val,blue_val,pink_val,tracker[coin]['close'][-1],in_position) == True and in_position == False:
                print("OPEN SHORT")

                order_succeed = Order(SIDE_BUY,atr_val,'open_short',tracker[coin]['close'][-1],pairup,pairdown,symbolup,symboldown)
                if order_succeed:
                    in_position = True
                    ref.update({"in_position": True})

            elif Exit_short(adx_val,red_val,yellow_val,green_val,brown_val,blue_val,pink_val,tracker[coin]['close'][-1],in_position,position) == True and in_position == True and position == 'short':
                print("CLOSE SHORT")

                order_succeed = Order(SIDE_SELL,atr_val,'close_short',tracker[coin]['close'][-1],pairup,pairdown,symbolup,symboldown)
                if order_succeed:
                    SL = 0
                    ref.update({"SL": 0})
                    in_position = False
                    ref.update({"in_position": False})
            #checking condition
    # else:
    #     print("STOP LOSS [INACTIVE]: SL {} , PRICE {}".format(SL,float(close_price)))




app = Flask(__name__)
CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'
ws = websocket.WebSocketApp(SOCKET, on_open=on_open, on_close=on_close, on_message=on_message)


def encode_auth_token(user_id):
    """
    Generates the Auth Token
    :return: string
    """
    try:
        payload = {
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=0, seconds=1000),
            'iat': datetime.datetime.utcnow(),
            'sub': user_id
        }
        # print(payload)
        return jwt.encode(
            payload,
            os.environ.get("JWT_KEY", "leptoncap"),
            algorithm='HS256'
        )
    except Exception as e:
        print(e)
        return e

def decode_auth_token(auth_token):
    """
    Decodes the auth token
    :param auth_token:
    :return: integer|string
    """
    try:
        key = os.environ.get("JWT_KEY", "leptoncap")
        payload = jwt.decode(auth_token, key, algorithms=["HS256"])
        return payload['sub']
    except jwt.ExpiredSignatureError:
        return 'Signature expired. Please log in again.'
    except jwt.InvalidTokenError:
        return 'Invalid token. Please log in again.'

def check_auth(token):
    if token:
        res = decode_auth_token(token)
        # print(res)
        #perform search in firebase
        users_ref = db.collection(u'users')
        docs = users_ref.stream()

        for doc in docs:
            if doc.id == res:
                return True
            else:
                return False
    else:
        return False

def compare(username,password):
    users = db.collection(u'users').where('username', '==', username).stream()
    # print(users)
    for user in users:
        obj = user.to_dict()
        if obj['username'] == username:
            if obj['password'] == password:
                return user.id
            else:
                return False
        else:
            return False

def authentication(auth_headers):
    if auth_headers is None:
        return False
    auth_token = auth_headers.split(' ')[1]
    # print(auth_token)
    if check_auth(auth_token):
        return True
    else:
        return False

def run_server():
    #set the defaul vars
    print("RUNNING...")
    ws.run_forever()
    return


@app.route('/control')
def control():
    return render_template('home.html')

@app.route('/signin', methods=['POST'])
def signin():
    username = request.form.get('username')
    password = request.form.get('password')
    user_id = compare(username,password)
    if user_id:
        # print(user_id)
        token = encode_auth_token(user_id)
        return jsonify(token=token, auth=True)
    else:
        return jsonify(data="incorrect credentials", auth=False)

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/forbidden')
def forbidden():
    return render_template('403.html')

@app.route('/checkauth')
def checkauth():
    auth_headers = request.headers.get('Authorization')
    if authentication(auth_headers):
        return jsonify(auth=True)
    else:
        return jsonify(auth=False)

@app.route('/status')
def status():
    global is_online
    print("Get status")
    # sys.stdout.write("Get status" + '\n')
    # auth_headers = request.headers.get('Authorization')
    # if authentication(auth_headers):
    return jsonify(active=is_online)
    # else:
    #     return jsonify(error="403")

@app.route('/ethup')
def ethup():
    current_USDT = client.get_asset_balance(asset='ETHUP')
    response = jsonify(balance=current_USDT['free'])
    response.headers.add('Access-Control-Allow-Origin', '*')
    auth_headers = request.headers.get('Authorization')
    if authentication(auth_headers):
        return response
    else:
        return jsonify(error="403")


@app.route('/ethdown')
def ethdown():
    current_USDT = client.get_asset_balance(asset='ETHDOWN')
    response = jsonify(balance=current_USDT['free'])
    response.headers.add('Access-Control-Allow-Origin', '*')
    auth_headers = request.headers.get('Authorization')
    if authentication(auth_headers):
        return response
    else:
        return jsonify(error="403")

@app.route('/usdt')
def usdt():
    current_USDT = client.get_asset_balance(asset='USDT')
    print(current_USDT)
    response = jsonify(balance=current_USDT['free'])
    response.headers.add('Access-Control-Allow-Origin', '*')
    auth_headers = request.headers.get('Authorization')
    if authentication(auth_headers):
        return response
    else:
        return jsonify(error="403")

@app.route('/connect', methods=['POST'])
def connect():
    global ws, t1
    if request.method == 'POST':
        auth_headers = request.headers.get('Authorization')
        if authentication(auth_headers):
            Init_candle(120)
            print("Init success, Bot is ready...")
            response = jsonify(status="Running")
            response.headers.add('Access-Control-Allow-Origin', '*')

            t1 = threading.Thread(target=run_server)
            t1.start()
            return response
        else:
            return jsonify(error="403")


@app.route('/disconnect', methods=['POST'])

def disconnect():
    global ws, tracker, LATEST_BOUGHT, SL, sticks, in_position, SL_active,t1,coin
    if request.method == 'POST':
        # auth_headers = request.headers.get('Authorization')
        # if authentication(auth_headers):
        print("Bot shutdown")
        ws.close()
        t1.join()
        LATEST_BOUGHT = 0
        SL = 0
        # Current_ATR = 0
        sticks = 0
        in_position = False
        SL_active = False
        tracker[coin]["close"] = []
        tracker[coin]["open"] = []
        tracker[coin]["high"] = []
        tracker[coin]["low"] = []
        tracker[coin]["hl2"] = []

        print(tracker)
        # activation = False
        # sys.stdout.write("Bot shutdown" +'\n')
        # sys.stdout.flush()
        response = jsonify(status="shutdown")
        response.headers.add('Access-Control-Allow-Origin', '*')
    return response
        # else:
        #     return jsonify(error="403")


if __name__ == '__main__':
    # app.secret_key='secret123'
    port = int(os.environ.get("PORT", 5000))
    Init_candle(120)
    print("Init success, Bot is ready...")
    t1 = threading.Thread(target=run_server)
    t1.start()
    app.run(host='0.0.0.0', port=port, debug=False)

