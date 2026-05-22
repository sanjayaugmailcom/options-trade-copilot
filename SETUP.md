# Options Strategy Testing - Setup & Usage Guide

## Quick Start

### 1. Create src directory
```bash
mkdir src
```

### 2. Copy React files
The following files need to be created in the `src/` folder:
- `main.jsx` - React entry point
- `App.jsx` - Main app component  
- `App.css` - App styles
- `index.css` - Global styles

These files are provided in this package.

### 3. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 4. Install Node dependencies
```bash
npm install
```

### 5. Configure environment
Create a `.env` file in the root directory:
```
POLYGON_API_KEY=iBy683ZpTFfOboGnrRY21GGcaV6isZNH
```

### 6. Run Backend (Terminal 1)
```bash
python main.py
```
Backend starts on http://localhost:8000

### 7. Run Frontend (Terminal 2)
```bash
npm run dev
```
Frontend starts on http://localhost:3000

## What's Included

### Backend (main.py)
- FastAPI server for options data and strategy calculations
- Integrates with Polygon.io API
- Calculates payoffs for 4 options strategies:
  - Covered Call
  - Protective Put
  - Bull Call Spread
  - Iron Condor

### Frontend (React)
- Interactive UI for entering symbols and expirations
- Real-time strategy comparison
- Visual payoff indicators
- Responsive design

### Project Structure
```
├── main.py              # FastAPI backend
├── requirements.txt     # Python dependencies
├── package.json        # Node dependencies
├── vite.config.js      # Vite config
├── index.html          # HTML entry point
├── src/
│   ├── main.jsx        # React entry
│   ├── App.jsx         # Main component
│   ├── App.css         # Styles
│   └── index.css       # Global styles
├── README.md           # This file
└── .env.example        # API key template
```

## Usage

1. Open http://localhost:3000
2. Enter a stock symbol (e.g., SPY, AAPL)
3. Select expiration date
4. Click "Backtest Strategies"
5. View results with metrics and comparison table

## API Reference

### GET /health
Health check endpoint

### GET /backtest/{symbol}/{expiration}
Backtest strategies for a given symbol and expiration
- Returns strategy metrics including max profit/loss, breakeven, and risk/reward ratio

## Notes

- Use existing files in src/ directory when creating the React app
- Ensure .env file has your Polygon.io API key
- Backend must be running before frontend can fetch data
- The app uses real-time option prices from Polygon.io

## Troubleshooting

**"API key error"**: Check that POLYGON_API_KEY in .env is correct

**"No options found"**: Symbol or expiration might not have options available

**"Connection refused"**: Make sure backend (http://localhost:8000) is running

**"Module not found"**: Run `npm install` to install Node dependencies
