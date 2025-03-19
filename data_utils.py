import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import re
import pytz

def get_forex_data(pair="AUDUSD=X", interval="1h", period="5d"):
    """
    Fetch forex data from Yahoo Finance.
    
    Args:
        pair (str): Forex pair symbol (e.g., 'AUDUSD=X')
        interval (str): Time interval between data points ('15m', '1h', '4h')
        period (str): How far back to get data ('5d', '7d', etc.)
    
    Returns:
        list: List of dicts with date and close price
    """
    # Map our intervals to yfinance format
    interval_map = {
        "15m": "15m",
        "1h": "60m",
        "4h": "4h"
    }
    
    try:
        # Get data from yfinance
        data = yf.download(
            tickers=pair,
            interval=interval_map[interval],
            period=period,
            progress=False
        )
        
        # If no data returned
        if data.empty:
            print(f"No data returned for {pair}")
            return []
        
        # Convert to our format
        stock_data = [{
            "date": index.strftime("%d-%b-%Y %H:%M"),
            "close": float(row["Close"])
        } for index, row in data.iterrows()]
        
        return stock_data
    
    except Exception as e:
        print(f"Error fetching data for {pair}: {e}")
        return []

def convert_to_aest(utc_time):
    """
    Convert UTC time to AEST (Australian Eastern Standard Time).
    
    Args:
        utc_time (str): Time string in format '%d-%b-%Y %H:%M'
    
    Returns:
        str: Converted time string in same format
    """
    try:
        utc_dt = datetime.strptime(utc_time, "%d-%b-%Y %H:%M")
        utc_dt = utc_dt.replace(tzinfo=pytz.UTC)
        aest = pytz.timezone("Australia/Sydney")
        aest_time = utc_dt.astimezone(aest)
        return aest_time.strftime("%d-%b-%Y %H:%M")
    except Exception as e:
        print(f"Error converting time: {e}")
        return utc_time

def generate_future_projections_from_point(stock_data, start_idx, future_points=10, num_lines=1):
    """
    Generate projections starting from a specific point in the price history.
    
    Args:
        stock_data: Full price history data
        start_idx: Index in stock_data to start the projection from
        future_points: Number of points to project into the future
        num_lines: Number of projection lines to generate
    
    Returns:
        List of projection dictionaries
    """
    if not stock_data or start_idx >= len(stock_data):
        return []
    
    # Get data up to the starting point (we'll search for patterns in this data)
    data_subset = stock_data[:start_idx+1]
    
    # Create pattern string (U for up, D for down)
    # We'll look at up to 8 points before the start_idx to find patterns
    pattern_length = min(8, start_idx)
    pattern_data = data_subset[-pattern_length-1:]
    
    if len(pattern_data) <= 1:
        return []
    
    result_string = ''.join(['U' if pattern_data[i+1]["close"] >= pattern_data[i]["close"] else 'D'
                            for i in range(len(pattern_data)-1)])
    
    # Find pattern matches in the full dataset
    index_dict = {}
    for length in range(min(len(result_string), 8), max(5, min(len(result_string)-1, 5)), -1):
        if length <= 0:
            continue
            
        string_to_match = result_string[-length:]
        
        # Create a string to search in (excluding the current pattern)
        if len(stock_data) <= 1:
            return []
            
        search_string = ''.join(['U' if stock_data[i]["close"] >= stock_data[i-1]["close"] else 'D'
                                for i in range(1, max(1, len(stock_data)-pattern_length))])
        
        matches = [match.start() for match in re.finditer(re.escape(string_to_match), search_string)]
        if len(matches) > 1:
            for matched_index in matches:
                if matched_index not in index_dict and matched_index + pattern_length < start_idx:
                    index_dict[matched_index] = length
    
    # Get the specific point we're starting from
    start_point = stock_data[start_idx]
    start_close = start_point["close"]
    start_date = datetime.strptime(start_point["date"], "%d-%b-%Y %H:%M")
    
    # Generate projections
    future_projections = []
    matched_keys = list(index_dict.keys())[:num_lines]
    
    for key in matched_keys:
        pattern_length = index_dict[key]
        future_prices = [start_close]
        future_dates = [start_date]
        
        # Get price changes from historical pattern
        for i in range(future_points):
            pattern_idx = key + pattern_length + i
            if pattern_idx + 1 < len(stock_data):
                price_change = (stock_data[pattern_idx]["close"] - stock_data[pattern_idx+1]["close"]) / stock_data[pattern_idx+1]["close"]
                future_prices.append(future_prices[-1] * (1 + price_change))
                
                # Calculate future dates based on the interval between data points
                if i > 0:
                    # Determine the interval from the data
                    if len(stock_data) > 1:
                        curr_date = datetime.strptime(stock_data[0]["date"], "%d-%b-%Y %H:%M")
                        next_date = datetime.strptime(stock_data[1]["date"], "%d-%b-%Y %H:%M")
                        delta = curr_date - next_date  # Reverse the order as stock_data is reversed
                        future_dates.append(future_dates[-1] + delta)
                    else:
                        # Default to 1 hour if we can't determine
                        future_dates.append(future_dates[-1] + timedelta(hours=1))
                else:
                    # For the first projection point, use the interval from data if available
                    if start_idx + 1 < len(stock_data):
                        next_date = datetime.strptime(stock_data[start_idx+1]["date"], "%d-%b-%Y %H:%M")
                        future_dates.append(next_date)
                    else:
                        # Fallback to estimating interval
                        if len(stock_data) > 1:
                            date1 = datetime.strptime(stock_data[0]["date"], "%d-%b-%Y %H:%M")
                            date2 = datetime.strptime(stock_data[1]["date"], "%d-%b-%Y %H:%M")
                            interval_minutes = abs((date2 - date1).total_seconds() / 60)
                            future_dates.append(future_dates[-1] + timedelta(minutes=interval_minutes))
                        else:
                            # Default to 60 minutes if we can't determine
                            future_dates.append(future_dates[-1] + timedelta(hours=1))
        
        # Format the projection data
        future_line = [{"date": future_dates[i].strftime("%d-%b-%Y %H:%M"), "close": future_prices[i]} for i in range(len(future_prices))]
        
        future_projections.append({
            "label": f"Projection from point {start_idx+1}/{len(stock_data)}", 
            "data": future_line,
            "pattern_length": pattern_length
        })
    
    return future_projections