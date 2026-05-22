"""FastAPI backend for options strategy testing"""
import os
from datetime import datetime, timedelta
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import numpy as np
from typing import List, Dict, Any

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
POLYGON_BASE_URL = "https://api.polygon.io"

# Models
class OptionContract(BaseModel):
    strike: float
    expiration: str
    call_bid: float
    call_ask: float
    put_bid: float
    put_ask: float
    open_interest: int

class StrategyResult(BaseModel):
    name: str
    description: str
    max_profit: float
    max_loss: float
    breakeven: List[float]
    entry_cost: float
    exit_price: float
    return_pct: float
    risk_reward_ratio: float

class BacktestResults(BaseModel):
    symbol: str
    spot_price: float
    expiration: str
    strategies: List[StrategyResult]

# Polygon.io API functions
async def get_option_chain(symbol: str, expiration: str) -> List[OptionContract]:
    """Fetch option chain data from Polygon.io"""
    async with httpx.AsyncClient() as client:
        url = f"{POLYGON_BASE_URL}/v3/snapshot/options/{symbol}/{expiration}"
        params = {"apiKey": POLYGON_API_KEY, "limit": 100}
        
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            options = []
            for result in data.get("results", []):
                options.append(OptionContract(
                    strike=result["strike_price"],
                    expiration=expiration,
                    call_bid=result.get("last_quote", {}).get("bid", 0),
                    call_ask=result.get("last_quote", {}).get("ask", 0),
                    put_bid=result.get("last_quote", {}).get("bid", 0),
                    put_ask=result.get("last_quote", {}).get("ask", 0),
                    open_interest=result.get("open_interest", 0)
                ))
            return options
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to fetch options: {str(e)}")

async def get_stock_price(symbol: str) -> float:
    """Get current stock price from Polygon.io"""
    async with httpx.AsyncClient() as client:
        url = f"{POLYGON_BASE_URL}/v3/snapshot/stocks/{symbol}"
        params = {"apiKey": POLYGON_API_KEY}
        
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            return data["status"] == "OK" and data["results"]["last_trade"]["price"] or 0
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to fetch stock price: {str(e)}")

# Strategy calculation functions
def covered_call(stock_price: float, strike: float, call_premium: float, 
                 short_call_premium: float) -> Dict[str, Any]:
    """Covered Call: Long stock + Short call"""
    entry_cost = stock_price - short_call_premium
    max_profit = (strike - stock_price) + short_call_premium
    max_loss = stock_price - short_call_premium
    
    return {
        "max_profit": max(max_profit, 0),
        "max_loss": max(max_loss, 0),
        "breakeven": [entry_cost],
        "entry_cost": entry_cost
    }

def protective_put(stock_price: float, strike: float, put_premium: float) -> Dict[str, Any]:
    """Protective Put: Long stock + Long put"""
    entry_cost = stock_price + put_premium
    max_loss = (entry_cost - strike) if strike < entry_cost else 0
    max_profit = float('inf')
    
    return {
        "max_profit": max_profit,
        "max_loss": max_loss,
        "breakeven": [entry_cost],
        "entry_cost": entry_cost
    }

def bull_call_spread(stock_price: float, long_strike: float, short_strike: float,
                     long_premium: float, short_premium: float) -> Dict[str, Any]:
    """Bull Call Spread: Long call + Short call at higher strike"""
    net_debit = long_premium - short_premium
    max_profit = (short_strike - long_strike) - net_debit
    max_loss = net_debit
    
    return {
        "max_profit": max_profit,
        "max_loss": max_loss,
        "breakeven": [long_strike + net_debit],
        "entry_cost": net_debit
    }

def iron_condor(stock_price: float, put_strike: float, call_strike: float,
                long_put_premium: float, short_put_premium: float,
                long_call_premium: float, short_call_premium: float) -> Dict[str, Any]:
    """Iron Condor: Short call spread + Short put spread"""
    net_credit = (short_call_premium + short_put_premium) - (long_call_premium + long_put_premium)
    max_profit = net_credit
    call_width = call_strike * 0.05  # Assuming 5% width for example
    max_loss = call_width - net_credit
    
    return {
        "max_profit": max(max_profit, 0),
        "max_loss": max(max_loss, 0),
        "breakeven": [put_strike - net_credit, call_strike + net_credit],
        "entry_cost": -net_credit  # Credit received
    }

# API endpoints
@app.get("/health")
async def health():
    """Health check"""
    return {"status": "ok"}

@app.get("/backtest/{symbol}/{expiration}", response_model=BacktestResults)
async def backtest_strategies(symbol: str, expiration: str):
    """Run backtest for multiple strategies on given symbol and expiration"""
    
    # Fetch data
    stock_price = await get_stock_price(symbol)
    options = await get_option_chain(symbol, expiration)
    
    if not stock_price:
        raise HTTPException(status_code=404, detail=f"Could not fetch price for {symbol}")
    if not options:
        raise HTTPException(status_code=404, detail=f"No options found for {symbol} expiring {expiration}")
    
    # Find ATM and nearby strikes
    atm_idx = min(range(len(options)), key=lambda i: abs(options[i].strike - stock_price))
    atm = options[atm_idx]
    
    strategies = []
    
    # Covered Call (ATM short call)
    cc_result = covered_call(stock_price, atm.strike, 0, atm.call_bid)
    strategies.append(StrategyResult(
        name="Covered Call",
        description="Buy stock, sell ATM call",
        max_profit=cc_result["max_profit"],
        max_loss=cc_result["max_loss"],
        breakeven=cc_result["breakeven"],
        entry_cost=cc_result["entry_cost"],
        exit_price=atm.strike,
        return_pct=(cc_result["max_profit"] / cc_result["entry_cost"] * 100) if cc_result["entry_cost"] > 0 else 0,
        risk_reward_ratio=cc_result["max_profit"] / cc_result["max_loss"] if cc_result["max_loss"] > 0 else float('inf')
    ))
    
    # Protective Put (ATM long put)
    pp_result = protective_put(stock_price, atm.strike, atm.put_ask)
    strategies.append(StrategyResult(
        name="Protective Put",
        description="Buy stock, buy ATM put",
        max_profit=pp_result["max_profit"],
        max_loss=pp_result["max_loss"],
        breakeven=pp_result["breakeven"],
        entry_cost=pp_result["entry_cost"],
        exit_price=stock_price,
        return_pct=0,  # Placeholder
        risk_reward_ratio=0 if pp_result["max_loss"] == 0 else float('inf')
    ))
    
    # Bull Call Spread
    if atm_idx + 1 < len(options):
        long_call = atm
        short_call = options[atm_idx + 1]
        bcs_result = bull_call_spread(stock_price, atm.strike, short_call.strike, 
                                      long_call.call_ask, short_call.call_bid)
        strategies.append(StrategyResult(
            name="Bull Call Spread",
            description=f"Buy {atm.strike} call, sell {short_call.strike} call",
            max_profit=bcs_result["max_profit"],
            max_loss=bcs_result["max_loss"],
            breakeven=bcs_result["breakeven"],
            entry_cost=bcs_result["entry_cost"],
            exit_price=short_call.strike,
            return_pct=(bcs_result["max_profit"] / bcs_result["entry_cost"] * 100) if bcs_result["entry_cost"] > 0 else 0,
            risk_reward_ratio=bcs_result["max_profit"] / bcs_result["max_loss"] if bcs_result["max_loss"] > 0 else float('inf')
        ))
    
    # Iron Condor
    if atm_idx > 0 and atm_idx + 1 < len(options):
        put_leg = options[atm_idx - 1]
        call_leg = options[atm_idx + 1]
        ic_result = iron_condor(stock_price, put_leg.strike, call_leg.strike,
                                put_leg.put_ask, put_leg.put_bid,
                                call_leg.call_ask, call_leg.call_bid)
        strategies.append(StrategyResult(
            name="Iron Condor",
            description=f"Sell {put_leg.strike} put spread, sell {call_leg.strike} call spread",
            max_profit=ic_result["max_profit"],
            max_loss=ic_result["max_loss"],
            breakeven=ic_result["breakeven"],
            entry_cost=ic_result["entry_cost"],
            exit_price=(put_leg.strike + call_leg.strike) / 2,
            return_pct=(ic_result["max_profit"] / abs(ic_result["entry_cost"]) * 100) if ic_result["entry_cost"] != 0 else 0,
            risk_reward_ratio=ic_result["max_profit"] / ic_result["max_loss"] if ic_result["max_loss"] > 0 else float('inf')
        ))
    
    return BacktestResults(
        symbol=symbol,
        spot_price=stock_price,
        expiration=expiration,
        strategies=strategies
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
