# META Options Risk vs Reward Dashboard

This project is a React + Vite web app for fetching META option chain data and analyzing risk/reward.

## Features

- Fetches current META options data from Yahoo Finance
- Displays top call/put contracts ranked by 20% reward-to-premium ratio
- Renders a contract-specific payoff curve for selected options
- Shows premium, breakeven, and basic risk/reward statistics

## Setup

1. Install Node.js and npm.
2. Run `npm install` in the project root.
3. Install Python dependencies:

```powershell
python -m pip install -r requirements.txt
```

4. Start the Python backend server:

```powershell
npm run python-server
```

5. In a separate terminal start the frontend dev server:

```powershell
npm run dev
```

6. Open the displayed local URL in your browser.

The frontend proxies `/api` to the Python backend on `http://localhost:5179`, so it can call `/api/options/META` without CORS issues.

## Notes

- The app uses the Yahoo Finance endpoint: `https://query2.finance.yahoo.com/v7/finance/options/META`
- If you encounter CORS errors, you may need a local proxy or a backend server to fetch the data.
 - If you encounter CORS errors, start the proxy server with `npm run server` and keep it running alongside the dev server.

## Next enhancements

- Add a backend proxy for CORS-safe data retrieval
- Enable expiration selection with live updates
- Add filters for volume, open interest, and implied volatility
- Support custom strike scan ranges and payoff scenarios
