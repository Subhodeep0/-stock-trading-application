# Stock Trading App 📈

A Python Flask application for stock market trading with buy/sell orders, real-time stock prices, and portfolio tracking.

## Features ✨
- User registration & login
- Buy/Sell stocks
- Real-time stock prices (via yfinance)
- Portfolio tracking
- Order history
- Balance management ($10,000 starting balance)

## Tech Stack 🛠️
- Python 3.8+
- Flask
- MySQL
- yfinance API
- JWT Authentication

## Installation 📦

### Prerequisites
- Python 3.8+
- MySQL Server
- pip

### Steps

```bash
# 1. Clone repository
git clone https://github.com/Subhodeep0/stock-trading-app.git
cd stock-trading-app

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create MySQL database
mysql -u root -p
CREATE DATABASE stock_trading_db;
EXIT;

# 5. Configure .env
cp .env.example .env
# Edit .env with your MySQL password

# 6. Run application
python app.py
