import requests
import pandas as pd
import pandas_ta as ta
import time
import numpy as np
from datetime import datetime
import logging
import os

# === Ortam değişkenleri ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_IDS = os.getenv("CHAT_IDS").split(",")
COINS = os.getenv("COINS").split(",")

# === Telegram Bildirim Fonksiyonu ===
def send_telegram_message(message):
    for chat_id in CHAT_IDS:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": message}
        try:
            requests.post(url, data=payload)
        except Exception as e:
            print(f"Telegram hatası: {e}")

# === Veriyi Binance'ten Al ===
def get_klines(symbol, interval="1h", limit=100):
    url = f"https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    response = requests.get(url, params=params)
    data = response.json()
    df = pd.DataFrame(data, columns=[
        "timestamp", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "number_of_trades",
        "taker_buy_base", "taker_buy_quote", "ignore"
    ])
    df["close"] = df["close"].astype(float)
    df["volume"] = df["volume"].astype(float)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df

# === Teknik Analiz ===
def analyze(df):
    df["ema20"] = ta.ema(df["close"], length=20)
    df["ema50"] = ta.ema(df["close"], length=50)
    df["rsi"] = ta.rsi(df["close"], length=14)
    macd = ta.macd(df["close"])
    df["macd_hist"] = macd["MACDh_12_26_9"]

    last = df.iloc[-1]
    previous = df.iloc[-2]

    # === Sinyal Koşulları ===
    al_kosulu = (
        last["close"] > last["ema20"] > last["ema50"] and
        last["rsi"] > 50 and
        last["macd_hist"] > 0 and
        last["volume"] > previous["volume"]
    )
    sat_kosulu = (
        last["close"] < last["ema20"] < last["ema50"] and
        last["rsi"] < 45 and
        last["macd_hist"] < 0 and
        last["volume"] < previous["volume"]
    )

    guclu_al = al_kosulu and last["rsi"] > 60 and last["macd_hist"] > 0.5
    guclu_sat = sat_kosulu and last["rsi"] < 35 and last["macd_hist"] < -0.5

    yorum = ""
    if guclu_al:
        sinyal = "📈 GÜÇLÜ AL"
        yorum = "Fiyat EMA'ların üzerinde. RSI yüksek ve MACD pozitif. Hacim artıyor."
    elif al_kosulu:
        sinyal = "AL"
        yorum = "EMA ve RSI pozitif. MACD histogramı yukarıda. Yükseliş olasılığı var."
    elif guclu_sat:
        sinyal = "🔻 GÜÇLÜ SAT"
        yorum = "Fiyat EMA'ların altında. RSI düşük. MACD negatif. Hacim düşüyor."
    elif sat_kosulu:
        sinyal = "SAT"
        yorum = "EMA, RSI ve MACD düşüş gösteriyor."
    else:
        sinyal = "KARARSIZ"
        yorum = "Göstergeler net değil. Belirsiz bölgedeyiz."

    return sinyal, yorum, last["close"]

# === Balina Tespiti ===
def detect_whale(df):
    last = df.iloc[-1]
    mean_volume = df["volume"].mean()
    return last["volume"] > mean_volume * 3

# === Ana Bot Döngüsü ===
def run():
    while True:
        try:
            for coin in COINS:
                df = get_klines(coin)
                if df is None or df.empty:
                    continue

                sinyal, yorum, fiyat = analyze(df)
                is_whale = detect_whale(df)

                zaman = datetime.now().strftime("%Y-%m-%d %H:%M")
                mesaj = f"[{zaman}] {coin} fiyatı: {fiyat:.2f} → Sinyal: {sinyal}\nAçıklama: {yorum}"
                if is_whale:
                    mesaj += "\n🐋 Balina işlemi tespit edildi!"

                if sinyal in ["AL", "SAT", "📈 GÜÇLÜ AL", "🔻 GÜÇLÜ SAT"]:
                    send_telegram_message(mesaj)

                print(mesaj)

            time.sleep(60)
        except Exception as e:
            print(f"Hata: {e}")
            time.sleep(60)

if __name__ == "__main__":
    run()
