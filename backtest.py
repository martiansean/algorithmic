import talib
import numpy
import json
from datetime import datetime


latest_bought = 0
SL = 0
stop_long = 0
stop_short = 0
status = "none"
ATR_MULTIPLE = 3
RISK = 0.03

Entering = 0
long_win = 0
long_lose = 0
short_win = 0
short_lose = 0

long_profit = 0
short_profit = 0

sizer = 0

def ConvertTime(n):
    ts = int(n)/1000
    ts += (7 * 60 * 60)
    # if you encounter a "year is out of range" error the timestamp
    # may be in milliseconds, try `ts /= 1000` in that case
    # return datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    return datetime.utcfromtimestamp(ts).strftime('%d %b %Y, %H:%M:%S GMT')

def check_exit_long(adx, close, pink, blue, brown, green, yellow, status):
    # print(f"ADX {adx}, PRICE {close}")
    if status == 'long':
        if adx >= 0 and adx < 5 and close <= pink:
            # print("pink")
            print(f"ADX {adx}, PRICE {close}, COLOR-pink {pink}")
            return True
        elif adx >= 5 and adx < 15 and close <= blue:
            # print("blue")
            print(f"ADX {adx}, PRICE {close}, COLOR-blue {blue}")
            return True
        elif adx >= 15 and adx < 25 and close <= brown:
            # print("brown")
            print(f"ADX {adx}, PRICE {close}, COLOR-brown {brown}")
            return True
        elif adx >= 25 and adx < 35 and close <= green:
            # print("green")
            print(f"ADX {adx}, PRICE {close}, COLOR-green {green}")
            return True
        elif adx >= 35 and close < yellow:
            # print("yellow")
            print(f"ADX {adx}, PRICE {close}, COLOR-yellow {yellow}")
            return True
        else:
            return False
    else:
        return False

def check_exit_short(adx, close, pink, blue, brown, green, yellow, status):
    if status == 'short':
        if adx >= 0 and adx < 5 and close >= pink:
            # print("pink")
            print(f"ADX {adx}, PRICE {close}, COLOR-pink {pink}")
            return True
        elif adx >= 5 and adx < 15 and close >= blue:
            # print("blue")
            print(f"ADX {adx}, PRICE {close}, COLOR-blue {blue}")
            return True
        elif adx >= 15 and adx < 25 and close >= brown:
            # print("brown")
            print(f"ADX {adx}, PRICE {close}, COLOR-brown {brown}")
            return True
        elif adx >= 25 and adx < 35 and close >= green:
            # print("green")
            print(f"ADX {adx}, PRICE {close}, COLOR-green {green}")
            return True
        elif adx >= 35 and close > yellow:
            # print("yellow")
            print(f"ADX {adx}, PRICE {close}, COLOR-yellow {yellow}")
            return True
        else:
            return False
    else:
        return False

# def checkSL(price):
#     if price <= SL:
#         return True
#     else:
#         return False

class Account:
    def __init__(self):
        self.cash = 0
        self.coin = 0
        self.start = 0
        self.position = False
        self.current_bought = 0
        self.trades = 0
        self.buy_signal = []
        self.sell_signal = []
        self.price = []
    def SetCash(self,n):
        self.cash = n
        self.start = n
        self.coin = 0
        print("SET CASH TO: {} 🤑".format(n))
        return
    def GetCoinHolding(self):
        return self.coin
    ################################### NEED FIXING ##########################################
    def ENTER_LONG(self,cash,coin_price,time,ATR):
        global latest_bought, SL, status
        if self.position == False and status == "none":
            latest_bought = coin_price
            SL = round(latest_bought-(ATR*ATR_MULTIPLE),2)
            print("SIZE {} ENTER LONG: {} SL: {}         TIME: {}".format(cash,coin_price,SL,ConvertTime(time)))
            self.position = True
            self.trades += 1
            self.coin += cash/coin_price
            self.current_bought = self.cash
            self.cash -= cash
            status = "long"
        return

    def EXIT_LONG(self,coin_price):
        global latest_bought, SL, status
        if self.position == True and status == 'long':
            print("EXIT LONG: {}".format(coin_price))
            # self.trades += 1
            self.cash += self.coin*coin_price
            self.coin = 0
            SL = 0
            self.position = False
            status = "none"
        return

    def ENTER_SHORT(self,cash,coin_price,time,ATR):
        global latest_bought, SL, status
        if self.position == False and status == "none":
            latest_bought = coin_price
            SL = round(latest_bought+(ATR*ATR_MULTIPLE),2)
            print("SIZE {} ENTER SHORT: {} SL: {}         TIME: {}".format(cash,coin_price,SL,ConvertTime(time)))
            self.position = True
            self.trades += 1
            self.coin += cash/coin_price
            self.cash += self.coin*coin_price
            status = "short"
        return
    
    def EXIT_SHORT(self,coin_price):
        global latest_bought, SL, status
        if self.position == True and status=="short":
            print("EXIT SHORT:",coin_price)
            self.cash -= self.coin*coin_price
            self.coin = 0
            # self.trades += 1
            SL = 0
            self.position = False
            status = "none"
        return


    def GetBudget(self,ATR,price):
        global sizer
        delta = (ATR*ATR_MULTIPLE)/price
        risk_amount = RISK*self.cash
        size = round(risk_amount/delta,2)

        if size > self.cash:
            # print("SIZE(1): {}, ATR {}, BALANCE: {}".format(0.9*self.cash, ATR*ATR_MULTIPLE,self.cash))
            return 0.9*self.cash
        # print("SIZE(2): {}, ATR {}, BALANCE: {}".format(size,ATR*ATR_MULTIPLE,self.cash))
        sizer += 1
        return size
        # return self.cash
        

    def GetCurrentBought(self):
        return self.current_bought
    def GetTrades(self):
        return self.trades

    def Final(self,price):
        global stop, win
        print("STATUS: {}".format(status))

        if status == "short":
            self.EXIT_SHORT(price)
            print("COIN: {}".format(self.coin))
            print("CASH: {}".format(self.cash))

        elif status == "long":
            self.EXIT_LONG(price)
            print("COIN: {}".format(self.coin))
            print("CASH: {}".format(self.cash))

        elif status == "none":
            print("COIN: {}".format(self.coin))
            print("CASH: {}".format(self.cash))

        print("GROWTH: {}%".format( ((self.cash-self.start)/self.start)*100 ))
        print("NUMBER OF TRADES {}, SL-LONG {}, SL-SHORT {}".format(self.trades,stop_long,stop_short))
        # print(f"LONG-WIN {long_win}, SHORT-WIN {short_win}, LONG-LOSE {long_lose}, SHORT-LOSE {short_lose}")
        # print("WIN RATE {}".format(((long_win+short_win)/self.trades)*100))
        # print(f"LONG_PROFIT(%) {long_profit} SHORT_PROFIT(%) {short_profit}")
        print(f"sizer {sizer}")


class Indicator:
    def __init__(self):
        self.MACD_SIGNAL = None
        self.MACD = None
        self.MACDHIST = None
        self.AROONUP = None
        self.AROONDOWN = None
        self.AROON = None
        self.STOCH = None
        self.EMA = None
        self.CCI = None
        self.ATR = None
        self.blue = None
        self.brown = None
        self.yellow = None
        self.pink = None
        self.red = None
        self.green = None
        self.data = None
        self.close = []
        self.open = []
        self.high = []
        self.low = []
        self.time = []
        self.vol = []
        self.hl2 = []
        self.hlc3 = []

    def read(self,file_name):
        input_file = open(file_name)
        json_array = json.load(input_file)
        self.data = json_array
        for i in self.data:
            self.open.append(i["open"])
            self.close.append(i["close"])
            self.high.append(i["high"])
            self.low.append(i["low"])
            self.vol.append(i["volume"])
            self.time.append(i["time"])
            self.hl2.append((i['high'] + i['low'])/2)
            self.hlc3.append(( (i['high'] + i['low']) + i['close'] )/2)


        return
    def process(self):
        print("processing.....")
        macd, macdsignal, macdhist = talib.MACD(numpy.array(self.close), fastperiod=12, slowperiod=26, signalperiod=5)
        aroonosc = talib.AROONOSC(numpy.array(self.high), numpy.array(self.low), timeperiod=25)
        adx = talib.ADX(numpy.array(self.high),numpy.array(self.low),numpy.array(self.close),timeperiod=13)
        atr = talib.ATR(numpy.array(self.high), numpy.array(self.low), numpy.array(self.close), timeperiod=13)
        """
        keys :=> RED[3-2], YELLOW[5-3], GREEN[8-5], BROWN[13-8], BLUE[21-13], PINK[34-21], BLACK[55-34]
        """

        pink = talib.EMA(numpy.array(self.hl2),timeperiod=34)
        blue = talib.EMA(numpy.array(self.hl2),timeperiod=21)
        brown = talib.EMA(numpy.array(self.hl2), timeperiod=13)
        green = talib.EMA(numpy.array(self.hl2), timeperiod=8)
        yellow = talib.EMA(numpy.array(self.hl2), timeperiod=5)
        red = talib.EMA(numpy.array(self.hl2), timeperiod=3)

        period_10 = talib.SMA(numpy.array(self.hl2), timeperiod=20)
        period_5 = talib.SMA(numpy.array(self.hl2), timeperiod=10)
        # rsi = talib.RSI(numpy.array(self.close), timeperiod=13)

        self.MACD_SIGNAL = list(macdsignal)
        self.MACD = list(macd)
        self.MACDHIST = list(macdhist)
        self.ATR = list(atr)
        self.AROON = list(aroonosc)
        self.ADX = list(adx)
        self.red = list(red)
        self.yellow = list(yellow)
        self.green = list(green)
        self.brown = list(brown)
        self.blue = list(blue)
        self.pink = list(pink)
        self.p10 = list(period_10)
        self.p5 = list(period_5)
        #
        # self.ADX = list(adx)
        # print(self.blue)
        # print(len(self.blue))
        # while True:
        #     exit()

        return
    def Trade(self,Account):
        global SL, stop_long,stop_short, status, latest_bought, Entering, long_win, short_win,long_lose,short_lose, long_profit, short_profit
        Account.SetCash(10000)
        print("Initialize set holding to zero...", Account.GetCoinHolding())
        print("Initialize set budget to cash....", 10000)
        growth = ((self.close[-1] - self.close[0])/self.close[0])*100
        print("MARKET GROWTH => {}".format(growth) )
        # counter = 0
        for i in range(40,len(self.close)):

            if self.high[i] >= SL and SL >= self.low[i] and status == "long":

                # print("SL-LONG: {} at {}".format(SL,ConvertTime(self.time[i])))
                stop_long += 1
                long_lose += 1
                # print(f'STOP::LOSE-LONG::ENTER: {Entering}, EXIT: {SL}')
                # long_profit += (SL-Entering)/Entering
                Account.EXIT_LONG(SL)
                Entering = 0

            elif self.high[i] >= SL and SL >= self.low[i] and status == "short":

                # print("SL-SHORT: {} at {}".format(SL,ConvertTime(self.time[i])))
                stop_short += 1
                short_lose += 1
                # print(f'STOP::LOSE-SHORT::ENTER: {Entering}, EXIT: {SL}')
                # short_profit += (Entering-SL)/Entering
                Account.EXIT_SHORT(SL)
                Entering = 0

            if  self.p5[i] > self.p10[i] and status != "long":
            # if self.EMA12[i] > self.EMA26[i] and status == "none":
                # Entering = self.close[i]
                if status == "short":
                    Account.EXIT_SHORT(self.close[i])
                Account.ENTER_LONG(Account.GetBudget(self.ATR[i],self.close[i]),self.close[i],self.time[i],self.ATR[i])

            # elif self.GREEN[i-2] < self.EMA10[i] and self.RED[i-3] < self.EMA10[i] and self.BLUE[i-5] < self.EMA10[i]  and status == "long":
            # elif check_exit_long(self.ADX[i], self.close[i], self.pink[i-21], self.blue[i-13], self.brown[i-8], self.green[i-5], self.yellow[i-3], status) == True and self.AROON[i] < 50 and status == "long":

            #     if Entering < self.close[i]:
            #         # print(f'WIN-LONG::ENTER: {Entering}, EXIT: {self.close[i]}')
            #         long_win += 1
            #         # long_profit += (self.close[i] - Entering)/Entering
            #         Entering = 0
            #     else:
            #         # print(f'LOSE-LONG::ENTER: {Entering}, EXIT: {self.close[i]}')
            #         long_lose += 1
            #         # long_profit += (self.close[i] - Entering)/Entering
            #         Entering = 0
            #     Account.EXIT_LONG(self.close[i])

            elif self.p5[i] < self.p10[i] and status != "short":

                # Entering = self.close[i]
                if status == "long":
                    Account.EXIT_LONG(self.close[i])
                Account.ENTER_SHORT(Account.GetBudget(self.ATR[i],self.close[i]),self.close[i],self.time[i],self.ATR[i])

            # elif check_exit_short(self.ADX[i], self.close[i], self.pink[i-21], self.blue[i-13], self.brown[i-8], self.green[i-5], self.yellow[i-3], status) == True and self.AROON[i] > -50 and status == "short":
            # # elif self.close[i] > self.EMA12[i] and status == "long":

            #     if Entering > self.close[i]:
            #         # print(f'WIN-SHORT::ENTER: {Entering}, EXIT: {self.close[i]}')
            #         short_win += 1
            #         # short_profit += (Entering - self.close[i])/Entering
            #         Entering = 0
            #     else:
            #         # print(f'LOSE-SHORT::ENTER: {Entering}, EXIT: {self.close[i]}')
            #         short_lose += 1
            #         # short_profit += (Entering - self.close[i])/Entering
            #         Entering = 0
            #     Account.EXIT_SHORT(self.close[i])

        Account.Final(self.close[-1])

        return


acc = Account()
indi = Indicator()
indi.read("data.json")
indi.process()
indi.Trade(acc)
