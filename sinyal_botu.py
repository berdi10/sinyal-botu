# sinyal_botu.py
import requests
import pandas as pd
import pandas_ta as ta
import time
from datetime import datetime
from binance.client import Client
from binance.exceptions import BinanceAPIException

# === Telegram Ayarları ===
TELEGRAM_TOKEN = "8156647982:AAEC-qe-qMwCAMTljSCgavR9-JYLaFSVY2s"
CHAT_IDS = [
    "1544313911",
    "7003554214",
    "6305874508"
]

def send_telegram_message(message):
    for chat_id in CHAT_IDS:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message
        }
        requests.post(url, data=payload)

# === Binance Ayarları ===
API_KEY = ""
API_SECRET = ""
client = Client(API_KEY, API_SECRET)

# === İzlenecek Coinler ===
COINS = [
    "BTCUSDT", "ETHUSDT", "ETHFIUSDT",
    "TIAUSDT", "EIGENUSDT", "ARBUSDT", "XRPUSDT"
]

# === Önceki sinyallerin takibi ===
last_signals = {}

# === Destek/Direnç Hesaplama ===
def calculate_support_resistance(df):
    recent_lows = df['low'].tail(20)
    recent_highs = df['high'].tail(20)
    return round(recent_lows.min(), 2), round(recent_highs.max(), 2)

while True:
    print("\n================ Yeni tarama başlıyor ================")
    now = datetime.now()
    for coin in COINS:
        try:
            klines = client.get_klines(symbol=coin, interval=Client.KLINE_INTERVAL_1HOUR, limit=100)
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            df['close'] = df['close'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            df['volume'] = df['volume'].astype(float)

            df.ta.rsi(length=14, append=True)
            df.ta.stoch(length=14, append=True)
            df.ta.macd(append=True)
            df.ta.ema(length=20, append=True)
            df.ta.ema(length=50, append=True)

            last = df.iloc[-1]
            rsi = last['RSI_14']
            stoch_k = last['STOCHk_14_3_3']
            stoch_d = last['STOCHd_14_3_3']
            macd_hist = last['MACDh_12_26_9']
            ema20 = last['EMA_20']
            ema50 = last['EMA_50']
            volume = last['volume']
            support, resistance = calculate_support_resistance(df)

            signal = "YOK"
            if rsi > 60 and stoch_k > 60 and macd_hist > 0 and ema20 > ema50:
                if rsi > 70 and macd_hist > 0.01:
                    signal = "GÜÇLÜ AL"
                else:
                    signal = "AL"
            elif rsi < 45 and macd_hist < 0 and ema20 < ema50:
                signal = "SAT"

            print(f"⚪ {coin} | RSI: {round(rsi,2)}, Stoch: {round(stoch_k,1)}/{round(stoch_d,1)}, MACD: {round(macd_hist,4)}, EMA20/50: {round(ema20,2)}/{round(ema50,2)}, Vol: {round(volume,2)}, Sup: {support}, Res: {resistance}")

            if last_signals.get(coin) != signal and signal != "YOK":
                last_signals[coin] = signal

                message = (
                    f"\n📡 Yeni sinyal: {coin} → {signal}\n"
                    f"📊 RSI: {round(rsi,2)} | Stoch: {round(stoch_k,1)} / {round(stoch_d,1)} | MACD: {round(macd_hist,4)}\n"
                    f"📈 EMA20/50: {round(ema20,2)} / {round(ema50,2)}\n"
                    f"📦 Hacim: {round(volume,2)} | Destek: {support} | Direnç: {resistance}\n"
                    f"⏰ Zaman: {now.strftime('%Y-%m-%d %H:%M')}")

                send_telegram_message(message)
                for chat_id in CHAT_IDS:
                    print(f"✅ Mesaj gönderildi: {chat_id}")
                print(f"✅ Yeni sinyal: {coin} → {signal} gönderildi.")
            else:
                print(f"{coin} için sinyal değişmedi: {signal}")
        except BinanceAPIException as e:
            print(f"Binance API hatası: {e.message}")
        except Exception as e:
            print(f"Hata oluştu ({coin}): {str(e)}")
    time.sleep(60)
