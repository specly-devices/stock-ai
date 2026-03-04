import yfinance as yf
from dotenv import load_dotenv
import os
from supabase import create_client

load_dotenv()

# Test 1: Fetch a stock
ticker = yf.Ticker("RELIANCE.NS")
data = ticker.history(period="5d")
print("✅ Stock data working:")
print(data[['Close']].tail(3))

# Test 2: Supabase connection
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)
print("\n✅ Supabase connected successfully")

# Test 3: Add a test stock
result = supabase.table("stocks").insert({
    "symbol": "RELIANCE.NS",
    "company_name": "Reliance Industries",
    "in_portfolio": False
}).execute()
print("✅ Database write working")