# Options Strategy Testing with Polygon.io

A full-stack web application for backtesting options strategies using real-time data from Polygon.io's options API.

## Features

- **Real-time Options Data**: Fetches live options chains from Polygon.io
- **Multiple Strategies**: Backtest 4 common options strategies:
  - Covered Call
  - Protective Put
  - Bull Call Spread
  - Iron Condor
- **Detailed Metrics**: Max profit/loss, breakeven points, risk/reward ratios, return percentages
- **Interactive UI**: Modern React-based web interface with responsive design
- **Strategy Comparison**: Side-by-side comparison table of all strategies

## Tech Stack

**Backend:**
- FastAPI (Python)
- Uvicorn ASGI server
- Polygon.io API integration

**Frontend:**
- React 18
- Vite (build tool)
- Axios (HTTP client)

## Setup

### 1. Clone and Install

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Node dependencies
npm install
```

### 2. Configure API Key

Create a `.env` file:
```bash
cp .env.example .env
# Edit .env and add your Polygon.io API key
POLYGON_API_KEY=your_api_key_here
```

### 3. Run the Application

**Terminal 1 - Backend:**
```bash
python main.py
```
The backend will start on http://localhost:8000

**Terminal 2 - Frontend:**
```bash
npm run dev
```
The frontend will start on http://localhost:3000

## Usage

1. Enter a stock symbol (e.g., SPY, AAPL, TSLA)
2. Select an expiration date
3. Click "Backtest Strategies"
4. View strategy metrics and comparison

## API Endpoints

- `GET /health` - Health check
- `GET /backtest/{symbol}/{expiration}` - Run backtest for a symbol/expiration pair

## Strategy Definitions

### Covered Call
Buy stock + Sell ATM call option
- **Best for**: Generating income from existing stock positions
- **Max Profit**: Limited to call strike
- **Max Loss**: Stock position

### Protective Put
Buy stock + Buy ATM put option
- **Best for**: Hedging against downside risk
- **Max Profit**: Unlimited
- **Max Loss**: Capped at put strike

### Bull Call Spread
Buy ATM call + Sell higher strike call
- **Best for**: Bullish outlook with limited capital
- **Max Profit**: Width of spread minus cost
- **Max Loss**: Net debit paid

### Iron Condor
Short put spread + Short call spread
- **Best for**: Neutral outlook, high probability trades
- **Max Profit**: Net credit received
- **Max Loss**: Spread width minus credit

## Notes

- Strategy calculations use ATM (at-the-money) and nearby strikes
- Bid-ask spreads are factored into entry costs
- Returns are theoretical based on current option prices
- Real trading should consider slippage, commissions, and liquidity
