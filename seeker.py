import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import json
from tqdm import tqdm
from yahoo_fin import stock_info as si
from ta.trend import CCIIndicator

# Configure logging
logging.basicConfig(
    filename='stock_analysis.log',
    filemode='w',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def load_config(config_file='config.json'):
    """
    Load configuration from a JSON file.
    """
    try:
        with open(config_file, 'r') as file:
            config = json.load(file)
        logging.info("Configuration loaded successfully")
        return config
    except Exception as e:
        logging.error(f"Error loading configuration: {e}")
        raise

def fetch_nasdaq_tickers():
    """
    Fetches a list of all tickers from NASDAQ.
    """
    try:
        logging.info("Fetching NASDAQ ticker symbols")
        tickers = si.tickers_nasdaq()
        logging.info(f"Number of tickers fetched from NASDAQ: {len(tickers)}")
        return tickers
    except Exception as e:
        logging.error(f"Error fetching NASDAQ tickers: {e}")
        return []

def fetch_stock_data(ticker, start_date, end_date):
    """
    Fetches historical stock data for a given ticker and date range.
    """
    try:
        data = yf.download(ticker, start=start_date, end=end_date, progress=False)
        if data.empty or len(data) < 200:
            logging.warning(f"Insufficient data for {ticker}")
            return pd.DataFrame()
        return data
    except Exception as e:
        logging.error(f"Error fetching data for {ticker}: {e}")
        return pd.DataFrame()

def apply_indicators(data, config):
    """
    Applies SMA and CCI indicators to the data.
    """
    try:
        data = data.copy()
        data['SMA20'] = data['Close'].rolling(window=config['sma20_window'], min_periods=config['sma20_window']).mean()
        data['SMA200'] = data['Close'].rolling(window=config['sma200_window'], min_periods=config['sma200_window']).mean()
        cci = CCIIndicator(high=data['High'], low=data['Low'], close=data['Close'], window=config['cci_window'])
        data['CCI'] = cci.cci()
        data.dropna(inplace=True)  # Remove rows with NaN values resulting from rolling calculations
        return data
    except Exception as e:
        logging.error(f"Error applying indicators: {e}")
        return pd.DataFrame()

def check_cci_rise(data, config):
    """
    Checks if CCI has risen from below -100 to above +100 in the last 20 days.
    """
    try:
        cci_last_n_days = data['CCI'].tail(config['cci_window'])
        cci_min = cci_last_n_days.min()
        cci_current = cci_last_n_days.iloc[-1]
        if cci_min < -100 and cci_current > 100:
            logging.info(f"CCI criteria met: Min CCI={cci_min}, Current CCI={cci_current}")
            return True
        return False
    except Exception as e:
        logging.error(f"Error checking CCI rise: {e}")
        return False

def check_sma_crossover(data, config):
    """
    Checks for SMA20 crossing above SMA200 in the last specified days.
    """
    try:
        sma_diff = data['SMA20'] - data['SMA200']
        crossover = ((sma_diff.shift(1) <= 0) & (sma_diff > 0)).tail(config['days_before'])
        if crossover.any():
            logging.info("SMA crossover detected")
            return True
        return False
    except Exception as e:
        logging.error(f"Error checking SMA crossover: {e}")
        return False

def check_volume_and_price(data, config):
    """
    Checks if average volume > threshold and last close price > threshold.
    """
    try:
        avg_volume = data['Volume'].tail(50).mean()
        last_price = data['Close'].iloc[-1]
        if avg_volume > config['volume_threshold'] and last_price > config['price_threshold']:
            logging.info(f"Volume and price criteria met: Avg Volume={avg_volume}, Last Price={last_price}")
            return True
        return False
    except Exception as e:
        logging.error(f"Error checking volume and price: {e}")
        return False

def analyze_stocks(tickers, start_date, end_date, config):
    """
    Analyzes stocks based on defined criteria.
    """
    results = []
    for ticker in tqdm(tickers, desc="Analyzing...", ncols=10, bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}'):
        logging.info(f"Processing {ticker}")
        data = fetch_stock_data(ticker, start_date, end_date)
        if data.empty:
            continue
        if not check_volume_and_price(data, config):
            continue
        data = apply_indicators(data, config)
        if data.empty:
            continue
        if not check_cci_rise(data, config):
            continue
        if not check_sma_crossover(data, config):
            continue
        last_row = data.iloc[-1]
        result = {
            'Ticker': ticker,
            'Last Price': round(last_row['Close'], 2),
            'CCI': round(last_row['CCI'], 2),
            'SMA20': round(last_row['SMA20'], 2),
            'SMA200': round(last_row['SMA200'], 2),
            'Average Volume': int(data['Volume'].tail(50).mean())
        }
        results.append(result)
        logging.info(f"{ticker} added to results")
    return results

if __name__ == "__main__":
    # Load configuration from JSON file
    config = load_config()

    # Define date range (one year period)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)  # Last 1 year

    # Fetch ticker list
    tickers = fetch_nasdaq_tickers()

    if not tickers:
        logging.error("No tickers to process. Exiting.")
    else:
        # Analyze stocks
        results = analyze_stocks(tickers, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'), config)

        if results:
            # Add timestamp to the filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'nasdaq_stock_analysis_results_{timestamp}.csv'
            df_results = pd.DataFrame(results)
            df_results.to_csv(filename, index=False)
            print(f"Analysis complete. Results saved to '{filename}'.")
            logging.info(f"Analysis complete. Results saved to '{filename}'.")
        else:
            print("No stocks met the criteria.")
            logging.info("No stocks met the criteria.")
