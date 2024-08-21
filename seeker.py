import investpy
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import sys
import os
from tqdm import tqdm  # Import tqdm for progress bars
from ta.trend import CCIIndicator  # Correctly import the CCIIndicator

# Function to fetch stock data with enhanced error handling
def fetch_stock_data(ticker, start_date, end_date):
    try:
        # Redirect stderr to null to suppress yfinance error messages
        sys.stderr = open(os.devnull, 'w')
        data = yf.download(ticker, start=start_date, end=end_date, progress=False)  # Disable progress bar
        sys.stderr = sys.__stderr__  # Reset stderr to default
        if data.empty:
            raise ValueError(f"No data found for {ticker}")
        return data
    except ValueError as e:
        sys.stderr = sys.__stderr__  # Ensure stderr is reset in case of error
        return pd.DataFrame()
    except Exception as e:
        sys.stderr = sys.__stderr__  # Ensure stderr is reset in case of error
        return pd.DataFrame()

# Function to apply SMA and CCI indicators
def apply_indicators(data):
    # SMA
    data['SMA20'] = data['Close'].rolling(window=20).mean()
    data['SMA200'] = data['Close'].rolling(window=200).mean()

    # CCI
    cci_indicator = CCIIndicator(high=data['High'], low=data['Low'], close=data['Close'], window=20)
    data['CCI'] = cci_indicator.cci()

    return data

# Function to check for CCI rise from below -100 to above +100 within the last 20 days
def check_cci_rise(data, ticker):
    cci_last_20 = data['CCI'].iloc[-20:]  # Get the last 20 days of CCI values
    cci_min = cci_last_20.min()  # Find the minimum CCI value in the last 20 days
    cci_end = cci_last_20.iloc[-1]  # Find the CCI value at the end of the period

    was_below_minus_100 = cci_min < -100  # Check if CCI was below -100
    is_above_plus_100_at_end = cci_end > 100  # Check if CCI is above +100 at the end

    if was_below_minus_100 and is_above_plus_100_at_end:
        print(f"{ticker} passed CCI filter: CCI min = {cci_min}, CCI end = {cci_end}")
        return True
    return False

# Function to check for SMA crossover in the last 5 days
def check_sma_crossover(data, ticker):
    for i in range(-5, 0):  # Check the last 5 days
        if data['SMA20'].iloc[i] > data['SMA200'].iloc[i] and data['SMA20'].iloc[i-1] <= data['SMA200'].iloc[i-1]:
            print(f"{ticker} passed SMA filter: SMA20 crossed above SMA200 in the last 5 days")
            return True
    return False

# Function to search stocks
def search_stocks(tickers, start_date, end_date):
    selected_stocks = []
    for ticker in tqdm(tickers, desc="Processing tickers"):  # Add progress bar to loop
        data = fetch_stock_data(ticker, start_date, end_date)
        if not data.empty:
            # Check if there are at least 200 data points available
            if len(data) < 200:
                continue

            # Apply SMA and CCI indicators
            data = apply_indicators(data)

            # Check CCI filter first
            if check_cci_rise(data, ticker):
                # If CCI filter passes, check for SMA crossover
                if check_sma_crossover(data, ticker):
                    selected_stocks.append(ticker)

    return selected_stocks

# Fetching NYSE tickers using investpy
try:
    nyse_stocks = investpy.stocks.get_stocks(country='united states')
    nyse_tickers = nyse_stocks['symbol'].tolist()

    print(f"Number of stocks on NYSE: {len(nyse_tickers)}")

    # Define the date range
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')  # Start approximately 1 year ago
    end_date = datetime.now().strftime('%Y-%m-%d')

    # Search stocks with the defined SMA and CCI criteria
    selected_stocks = search_stocks(nyse_tickers, start_date, end_date)

    print(f"Stocks meeting the SMA crossover and CCI rise criteria: {selected_stocks}")
except Exception as e:
    print(f"Error fetching NYSE tickers: {e}")
