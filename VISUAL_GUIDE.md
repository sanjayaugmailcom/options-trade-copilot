# Options Strategy Testing - Visual Guide

## 📱 Application Flow

```
┌─────────────────────────────────────────────────────────────┐
│                      Browser (Port 3000)                    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  1. Enter Symbol (e.g., SPY)                        │  │
│  │  2. Select Expiration Date                          │  │
│  │  3. Click "Backtest Strategies"                     │  │
│  └──────────────────┬──────────────────────────────────┘  │
│                     │ (HTTP GET Request)                   │
└─────────────────────┼─────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              FastAPI Backend (Port 8000)                    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ GET /backtest/{symbol}/{expiration}               │  │
│  │                                                    │  │
│  │ 1. Fetch stock price from Polygon.io             │  │
│  │ 2. Fetch option chain from Polygon.io            │  │
│  │ 3. Calculate strategy payoffs:                   │  │
│  │    - Covered Call                                │  │
│  │    - Protective Put                              │  │
│  │    - Bull Call Spread                            │  │
│  │    - Iron Condor                                 │  │
│  │ 4. Return JSON with metrics                      │  │
│  └──────────────────┬──────────────────────────────┘  │
│                     │ (Polygon.io API Calls)          │
└─────────────────────┼────────────────────────────────┘
                      │
                      ▼
        ┌──────────────────────────────┐
        │     Polygon.io API           │
        │ (options, stock prices)      │
        └──────────────────────────────┘
```

## 🎯 Strategy Payoff Diagrams

### Covered Call (Long Stock + Short Call)
```
Profit
   |     ╱─────────
   |    ╱
   |   ╱
   |  ╱
──────────────────► Stock Price
   |
   | Max Profit = Strike - Entry Cost
```

### Protective Put (Long Stock + Long Put)
```
Profit
   |         ╱─────
   |        ╱
   |       ╱
   |      ╱
──────────╱──────► Stock Price
   |    ╱
   | Max Loss = Entry Cost - Put Strike
```

### Bull Call Spread (Long Call + Short Call)
```
Profit
   |      ╱───────
   |     ╱│
   |    ╱ │
   |   ╱  │
──────────┼───────► Stock Price
   |     │╱
   | Max Loss = Net Debit
```

### Iron Condor (Short Call Spread + Short Put Spread)
```
Profit
   |   ╲───────╱
   |    ╲     ╱
   |     ╲   ╱
   |      ╲ ╱
──────────╱───\──► Stock Price
   |    ╱     ╲
   | Max Loss = Width - Credit
```

## 📊 Results Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│                    Options Strategy Testing                │
│         Backtest options strategies using Polygon.io      │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Symbol: [SPY____]  Expiration: [2026-05-29]  [Backtest]  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  SPY                                                        │
│  Current Price: $450.25   Expiration: 2026-05-29  Strategies: 4 │
└─────────────────────────────────────────────────────────────┘

Strategy Cards (4 columns):
┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
│ Covered Call      │ │ Protective Put    │ │ Bull Call Spread  │
│                   │ │                   │ │                   │
│ Entry: $450.25    │ │ Entry: $465.50    │ │ Entry: $2.50      │
│ Max P: $0.00      │ │ Max P: Unlimited  │ │ Max P: $2.50      │
│ Max L: $450.25    │ │ Max L: $15.25     │ │ Max L: $2.50      │
│ Return: 0.00%     │ │ Return: -3.27%    │ │ Return: 100%      │
│ Risk/Reward: 0.00 │ │ Risk/Reward: ∞    │ │ Risk/Reward: 1.00 │
│ Breakeven: $450   │ │ Breakeven: $465   │ │ Breakeven: $452   │
└───────────────────┘ └───────────────────┘ └───────────────────┘

Comparison Table:
┌──────────────────┬────────────┬──────────────┬──────────────┬──────────────┐
│ Strategy         │ Entry Cost │ Max Profit   │ Max Loss     │ Return %     │
├──────────────────┼────────────┼──────────────┼──────────────┼──────────────┤
│ Covered Call     │ $450.25    │ $0.00        │ $450.25      │ 0.00%        │
│ Protective Put   │ $465.50    │ Unlimited    │ $15.25       │ -3.27%       │
│ Bull Call Spread │ $2.50      │ $2.50        │ $2.50        │ 100.00%      │
│ Iron Condor      │ -$0.75     │ $0.75        │ $4.25        │ 100.00%      │
└──────────────────┴────────────┴──────────────┴──────────────┴──────────────┘
```

## 🔌 API Request/Response Example

### Request
```
GET /backtest/SPY/2026-05-29
```

### Response
```json
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
    {
      "name": "Protective Put",
      "description": "Buy stock, buy ATM put",
      "max_profit": 1e+308,
      "max_loss": 15.25,
      "breakeven": [465.50],
      "entry_cost": 465.50,
      "exit_price": 450.25,
      "return_pct": -3.27,
      "risk_reward_ratio": 1e+308
    },
    {
      "name": "Bull Call Spread",
      "description": "Buy 450.25 call, sell 455.00 call",
      "max_profit": 2.50,
      "max_loss": 2.50,
      "breakeven": [452.75],
      "entry_cost": 2.50,
      "exit_price": 455.00,
      "return_pct": 100.00,
      "risk_reward_ratio": 1.00
    },
    {
      "name": "Iron Condor",
      "description": "Sell 450.25 put spread, sell 455.00 call spread",
      "max_profit": 0.75,
      "max_loss": 4.25,
      "breakeven": [445.50, 459.50],
      "entry_cost": -0.75,
      "exit_price": 452.50,
      "return_pct": 100.00,
      "risk_reward_ratio": 0.18
    }
  ]
}
```

## 🎨 Color Coding System

| Return % | Color  | Background                        |
|----------|--------|-----------------------------------|
| > 50%    | 🟢 Green  | Light green gradient              |
| 20-50%   | 🔵 Blue   | Light blue gradient               |
| 0-20%    | 🟡 Yellow | Light orange gradient             |
| < 0%     | 🔴 Red    | Light red gradient                |

## 📁 File Organization

```
project/
├── Backend
│   ├── main.py                 # All backend logic
│   ├── requirements.txt        # Python dependencies
│   └── .env                    # API keys (not in git)
│
├── Frontend
│   ├── src/App.jsx             # Main component logic
│   ├── src/App.css             # Styling
│   ├── src/main.jsx            # React entry
│   ├── src/index.css           # Global styles
│   ├── index.html              # HTML entry
│   ├── package.json            # NPM dependencies
│   └── vite.config.js          # Build config
│
├── Configuration
│   ├── .gitignore              # Git exclusions
│   ├── .env.example            # Template
│   └── setup.py                # Directory setup
│
└── Documentation
    ├── README.md               # Full docs
    ├── SETUP.md                # Setup guide
    └── PROJECT_SUMMARY.md      # This overview
```

## 🚀 Deployment Checklist

- [ ] Python 3.8+ installed
- [ ] Node.js 16+ installed
- [ ] Run: `python setup.py`
- [ ] Run: `pip install -r requirements.txt`
- [ ] Run: `npm install`
- [ ] Create `.env` with API key
- [ ] Test backend: `python main.py`
- [ ] Test frontend: `npm run dev`
- [ ] Open http://localhost:3000
- [ ] Test a strategy (e.g., SPY for next Friday)
- [ ] Verify results display correctly

---

**Ready to backtest options strategies with real Polygon.io data!** 🎯📈
