import investpy
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta  # Import timedelta
import sys
import os

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
        # print(f"Skipping {ticker}: {e}")
        return pd.DataFrame()
    except Exception as e:
        sys.stderr = sys.__stderr__  # Ensure stderr is reset in case of error
        # print(f"Skipping {ticker}: {e}")
        return pd.DataFrame()

# Function to apply SMA indicators
def apply_sma_indicators(data):
    # SMA
    data['SMA20'] = data['Close'].rolling(window=20).mean()
    data['SMA200'] = data['Close'].rolling(window=200).mean()
    return data

# Function to check for SMA crossover in the last 5 days
def check_sma_crossover(data):
    for i in range(-5, 0):  # Check the last 5 days
        if data['SMA20'].iloc[i] > data['SMA200'].iloc[i] and data['SMA20'].iloc[i-1] <= data['SMA200'].iloc[i-1]:
            return True
    return False

# Function to search stocks
def search_stocks(tickers, start_date, end_date):
    selected_stocks = []
    for ticker in tickers:
        data = fetch_stock_data(ticker, start_date, end_date)
        if not data.empty:
            # Check if there are at least 200 data points available
            if len(data) < 200:
                print(f"{ticker}: Not enough data points for SMA200 calculation (only {len(data)} available)")
                continue

            # Apply SMA indicators
            data = apply_sma_indicators(data)

            # Print the ticker, last close price, SMA20, and SMA200 before applying filters
            last_close = data['Close'].iloc[-1]
            sma20 = data['SMA20'].iloc[-1]
            sma200 = data['SMA200'].iloc[-1]
            # print(f"{ticker}: Last close price = {last_close}, SMA20 = {sma20}, SMA200 = {sma200}")

            # Check for SMA crossover in the last 5 days
            if check_sma_crossover(data):
                print(f"{ticker} crossed above SMA200 in the last 5 days: SMA20 = {sma20}, SMA200 = {sma200}")
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

    # Search stocks with the defined SMA criteria
    selected_stocks = search_stocks(nyse_tickers, start_date, end_date)

    print(f"Stocks meeting the SMA crossover criteria: {selected_stocks}")
except Exception as e:
    print(f"Error fetching NYSE tickers: {e}")
