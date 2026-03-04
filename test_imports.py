import sys
print(f"Python: {sys.version}")

modules = [
    "streamlit", "pandas", "numpy", "plotly",
    "yfinance", "supabase", "dotenv"
]

for mod in modules:
    try:
        __import__(mod)
        print(f"✅ {mod}")
    except Exception as e:
        print(f"❌ {mod}: {e}")