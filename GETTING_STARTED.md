# 📈 Options Strategy Testing with Polygon.io

A complete full-stack web application for testing and analyzing options trading strategies using real-time data from Polygon.io's (now called Massive) options API.

**Status:** ✅ Ready to Deploy

---

## 🎯 What This Does

This application fetches live options data from Polygon.io and backtests four popular options strategies:

1. **Covered Call** - Generate income from stock holdings
2. **Protective Put** - Hedge downside risk
3. **Bull Call Spread** - Leverage bullish moves with limited capital
4. **Iron Condor** - Profit from neutral market conditions

The web interface displays detailed metrics for each strategy including max profit/loss, breakeven points, and risk/reward ratios.

---

## 🚀 Quick Start (5 Minutes)

### 1. Setup Project Structure
```bash
python setup.py
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
npm install
```

### 3. Configure API Key
```bash
# Copy the example
copy .env.example .env

# Edit .env and add your Polygon.io API key
# POLYGON_API_KEY=your_key_here
```

### 4. Start Backend (Terminal 1)
```bash
python main.py
```
Backend will run on http://localhost:8000

### 5. Start Frontend (Terminal 2)
```bash
npm run dev
```
Frontend will run on http://localhost:3000

### 6. Open Browser
Navigate to http://localhost:3000

---

## 💻 Technology Stack

### Backend
- **Framework**: FastAPI (Python)
- **Server**: Uvicorn
- **HTTP Client**: httpx (async)
- **Data Processing**: numpy, pandas
- **API**: Polygon.io Options API

### Frontend
- **Framework**: React 18
- **Build Tool**: Vite
- **HTTP Client**: Axios
- **Styling**: CSS3 with gradients and animations

### Deployment Ready
- CORS enabled for frontend integration
- Environment variables for sensitive data
- Async operations for performance
- Responsive design for all devices

---

## 📊 Features

### Real-time Data
✅ Live stock prices from Polygon.io
✅ Complete option chains with all strikes
✅ Bid-ask spreads factored into calculations
✅ Automatic expiration date suggestions (next 10 Fridays)

### Strategy Analysis
✅ Maximum profit calculations
✅ Maximum loss calculations  
✅ Breakeven point identification
✅ Risk/reward ratio analysis
✅ Return percentage calculations

### User Interface
✅ Symbol input (auto-uppercase)
✅ Date picker for expirations
✅ Color-coded strategy cards (green/blue/yellow/red)
✅ Visual payoff indicators
✅ Comparison table for easy analysis
✅ Mobile-responsive design

---

## 📁 Project Files

```
options-strategy-testing/
│
├── Backend
│   ├── main.py                      # FastAPI application
│   ├── requirements.txt             # Python packages
│   └── .env                         # API keys (create from .env.example)
│
├── Frontend  
│   ├── src/
│   │   ├── main.jsx                # React entry point
│   │   ├── App.jsx                 # Main component
│   │   ├── App.css                 # Component styles
│   │   └── index.css               # Global styles
│   ├── index.html                  # HTML template
│   ├── package.json                # NPM dependencies
│   └── vite.config.js              # Vite configuration
│
├── Setup & Config
│   ├── setup.py                    # Creates src directory
│   ├── setup.bat                   # Windows setup script
│   ├── .env.example                # API key template
│   └── .gitignore                  # Git exclusions
│
└── Documentation
    ├── README.md                   # This file
    ├── SETUP.md                    # Detailed setup
    ├── PROJECT_SUMMARY.md          # Full overview
    ├── VISUAL_GUIDE.md             # Architecture & diagrams
    └── GETTING_STARTED.md          # Step-by-step guide
```

---

## 🔧 Configuration

### Environment Variables (.env)
```
POLYGON_API_KEY=your_api_key_here
```

Get your free API key from https://polygon.io/

### Backend Configuration (main.py)
```python
# Port configuration
app.run(host="0.0.0.0", port=8000)
```

### Frontend Configuration (vite.config.js)
```javascript
server: {
  port: 3000,
  proxy: {
    '/api': 'http://localhost:8000'  // Backend proxy
  }
}
```

---

## 📈 How It Works

### User Journey
```
1. User enters stock symbol (e.g., "SPY")
2. User selects expiration date
3. User clicks "Backtest Strategies"
4. Frontend sends HTTP GET to backend
5. Backend fetches data from Polygon.io
6. Backend calculates strategy payoffs
7. Backend returns JSON response
8. Frontend displays results
```

### Strategy Calculation Flow
```
Input: Symbol + Expiration
  ↓
Fetch current stock price
  ↓
Fetch option chain (all strikes)
  ↓
Find ATM options
  ↓
Calculate each strategy:
  - Entry cost
  - Max profit
  - Max loss
  - Breakeven points
  - Risk/reward ratio
  ↓
Return results as JSON
  ↓
Display in UI
```

---

## 🎓 Strategy Definitions

### Covered Call
**Position**: Long 100 shares + Short 1 call
- **Best for**: Income generation
- **Entry**: Sell call against existing shares
- **Max Profit**: Strike price - Entry cost
- **Max Loss**: Entry cost (if stock drops to zero)
- **Breakeven**: Entry cost - Call premium

### Protective Put
**Position**: Long 100 shares + Long 1 put
- **Best for**: Downside protection
- **Entry**: Buy put as insurance
- **Max Profit**: Unlimited
- **Max Loss**: Entry cost - Put strike
- **Breakeven**: Entry cost + Put premium

### Bull Call Spread
**Position**: Long 1 call + Short 1 call (higher strike)
- **Best for**: Bullish outlook, limited capital
- **Entry**: Net debit (long call - short call)
- **Max Profit**: Spread width - Entry cost
- **Max Loss**: Entry cost
- **Breakeven**: Long strike + Entry cost

### Iron Condor
**Position**: Short put spread + Short call spread
- **Best for**: Neutral outlook, probability trades
- **Entry**: Net credit
- **Max Profit**: Credit received
- **Max Loss**: Spread width - Credit
- **Breakeven**: Two points (put strike - credit, call strike + credit)

---

## 🌐 API Reference

### Health Check
```
GET http://localhost:8000/health

Response:
{
  "status": "ok"
}
```

### Backtest Strategies
```
GET http://localhost:8000/backtest/{symbol}/{expiration}

Parameters:
- symbol: Stock ticker (e.g., "SPY", "AAPL")
- expiration: Date in YYYY-MM-DD format

Example:
GET http://localhost:8000/backtest/SPY/2026-05-29

Response:
{
  "symbol": "SPY",
  "spot_price": 450.25,
  "expiration": "2026-05-29",
  "strategies": [
    {
      "name": "Covered Call",
      "description": "Buy stock, sell ATM call",
      "max_profit": 0.00,
      "max_loss": 450.25,
      "breakeven": [450.25],
      "entry_cost": 450.25,
      "exit_price": 450.25,
      "return_pct": 0.00,
      "risk_reward_ratio": 0.00
    },
    ...
  ]
}
```

---

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| "Module not found" | Run `pip install -r requirements.txt && npm install` |
| "Connection refused" | Ensure backend is running on port 8000 |
| "No options found" | Symbol may not have options, or date doesn't exist |
| "POLYGON_API_KEY error" | Check your .env file has the correct API key |
| "Port 3000 in use" | Change port in vite.config.js or kill the process |
| "Port 8000 in use" | Change port in main.py or kill the process |

---

## 📝 Example Usage

### Step 1: Input
```
Symbol: SPY
Expiration: 2026-05-29
```

### Step 2: Results
The application shows:
- **Current Price**: $450.25
- **4 Strategy Cards** with metrics:
  - Covered Call: 0% return, 0.00 risk/reward
  - Protective Put: -3.27% return, ∞ risk/reward
  - Bull Call Spread: 100% return, 1.00 risk/reward
  - Iron Condor: 100% return, 0.18 risk/reward

### Step 3: Comparison Table
See all strategies side-by-side with:
- Entry cost
- Max profit
- Max loss
- Return percentage
- Risk/reward ratio

---

## ✅ Pre-flight Checklist

Before running the app:

- [ ] Python 3.8 or higher installed
- [ ] Node.js 16 or higher installed
- [ ] Polygon.io API key obtained
- [ ] `python setup.py` executed
- [ ] `pip install -r requirements.txt` completed
- [ ] `npm install` completed
- [ ] `.env` file created with API key
- [ ] Port 3000 and 8000 are available

---

## 🚀 Production Deployment

For production deployment:

1. Build React app: `npm run build`
2. Serve from dist/ directory
3. Use production WSGI server (gunicorn, etc.)
4. Implement authentication if needed
5. Add rate limiting for API endpoints
6. Use HTTPS/SSL certificates
7. Set appropriate CORS policies
8. Monitor API usage and costs

---

## 📚 Further Reading

- [Polygon.io Documentation](https://polygon.io/docs/options/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [Options Trading Guide](https://www.investopedia.com/options-trading-101-4925803)

---

## 💡 Tips & Tricks

### Common Test Cases
```
SPY (S&P 500 ETF) - Most liquid
AAPL (Apple) - Tech stock
TSLA (Tesla) - Volatile
QQQ (Nasdaq ETF) - Tech index
```

### Understanding the Metrics
- **Return %**: (Max Profit / Entry Cost) × 100
- **Risk/Reward**: Max Profit / Max Loss
- **Breakeven**: Stock price at which the strategy breaks even

### Reading the Color Codes
- 🟢 **Excellent** (>50%): High return potential
- 🔵 **Good** (20-50%): Solid return potential
- 🟡 **OK** (0-20%): Modest return potential
- 🔴 **Poor** (<0%): Negative return potential

---

## 📞 Support

### Issue With Polygon.io API
1. Check API status: https://status.polygon.io/
2. Verify API key is correct in .env
3. Check rate limits (free tier: 5 requests/minute)
4. Review API documentation: https://polygon.io/docs/

### Issue With Application
1. Check both terminals are running (backend & frontend)
2. Open browser console (F12) for error messages
3. Check backend logs for API errors
4. Verify ports 3000 and 8000 are available

---

## 📄 License

This project uses Polygon.io's public API. Refer to their terms of service.

---

## 🎉 You're Ready!

Everything is set up and ready to go. Follow the Quick Start section above to get running in 5 minutes.

**Happy backtesting!** 📈

---

Created: May 22, 2026
Status: ✅ Production Ready
Version: 1.0.0
