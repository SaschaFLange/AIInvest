import time
import yfinance as yf
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime

# Database Connection Settings
DB_HOST = "timescaledb"
DB_PORT = "5432"
DB_NAME = "stock_data"
DB_USER = "grafana_user"
DB_PASS = "secret_password"

# List of stock tickers to monitor
SYMBOLS = ["AAPL", "MSFT", "GOOGL", "NVDA", "RHM.DE"]
FETCH_INTERVAL_SECONDS = 60

def fetch_and_insert():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting stock data ingestion...")
    
    # Connect to TimescaleDB
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        cursor = conn.cursor()
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return

    records = []
    
    for symbol in SYMBOLS:
        print(f"Fetching data for {symbol}...")
        ticker = yf.Ticker(symbol)
        
        # Fetch the last 1 day of 1-minute interval market data
        df = ticker.history(period="1d", interval="1m")
        
        if df.empty:
            print(f"Warning: No data returned for {symbol}. Market might be closed or rate-limited.")
            continue

        for timestamp, row in df.iterrows():
            records.append((
                timestamp.to_pydatetime(),
                symbol,
                float(row['Open']),
                float(row['High']),
                float(row['Low']),
                float(row['Close']),
                int(row['Volume'])
            ))

    if not records:
        print("No new records to insert.")
        cursor.close()
        conn.close()
        return

    # Bulk insert into TimescaleDB with deduplication
    upsert_query = """
        INSERT INTO stock_prices (time, symbol, open, high, low, close, volume)
        VALUES %s
        ON CONFLICT (time, symbol) DO NOTHING;
    """

    try:
        execute_values(cursor, upsert_query, records)
        conn.commit()
        print(f"Successfully processed {len(records)} data points!")
    except Exception as e:
        conn.rollback()
        print(f"Error inserting data: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    print("Starting continuous stock ingestion service (Press Ctrl+C to stop)...")
    while True:
        try:
            fetch_and_insert()
        except Exception as e:
            print(f"Unexpected error in main loop: {e}")
        
        # Pause execution for the specified interval
        time.sleep(FETCH_INTERVAL_SECONDS)