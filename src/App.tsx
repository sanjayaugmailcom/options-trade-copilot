import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from 'react';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js';
import type { OptionContract } from './types';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

const YAHOO_OPTIONS_URL = '/api/options/';
const TOP_CANDIDATE_COUNT = 100;

function formatCurrency(value: number) {
  return value.toLocaleString('en-US', { style: 'currency', currency: 'USD' });
}

function safeNumber(value: number | null | undefined) {
  return Number(value ?? 0);
}

function buildPayoffSeries(contract: OptionContract, underlyingPrice: number, type: 'call' | 'put') {
  const range = 30;
  const min = underlyingPrice * 0.6;
  const max = underlyingPrice * 1.4;
  const step = (max - min) / range;

  const labels: string[] = [];
  const values: number[] = [];

  for (let i = 0; i <= range; i += 1) {
    const price = min + step * i;
    labels.push(price.toFixed(0));
    const intrinsic = type === 'call' ? Math.max(0, price - contract.strike) : Math.max(0, contract.strike - price);
    const profit = (intrinsic - contract.lastPrice) * 100;
    values.push(Number(profit.toFixed(2)));
  }

  return { labels, values };
}

function computeRewardRatio(contract: OptionContract, underlyingPrice: number, type: 'call' | 'put') {
  const targetPrice = type === 'call' ? underlyingPrice * 1.2 : underlyingPrice * 0.8;
  const intrinsic = type === 'call' ? Math.max(0, targetPrice - contract.strike) : Math.max(0, contract.strike - targetPrice);
  const profit = (intrinsic - contract.lastPrice) * 100;
  if (contract.lastPrice <= 0) return 0;
  return profit / (contract.lastPrice * 100);
}

function findBestContracts(contracts: OptionContract[], underlyingPrice: number, type: 'call' | 'put') {
  const enriched = contracts
    .map((contract) => ({
      contract,
      rewardRatio: computeRewardRatio(contract, underlyingPrice, type),
      breakeven:
        type === 'call'
          ? contract.strike + contract.lastPrice
          : contract.strike - contract.lastPrice,
      maxLoss: contract.lastPrice * 100,
      rewardAt20: type === 'call'
        ? Math.max(0, underlyingPrice * 1.2 - contract.strike - contract.lastPrice) * 100
        : Math.max(0, contract.strike - underlyingPrice * 0.8 - contract.lastPrice) * 100
    }))
    .sort((a, b) => b.rewardRatio - a.rewardRatio)
    .slice(0, TOP_CANDIDATE_COUNT);

  return enriched;
}

export default function App() {
  const [symbol, setSymbol] = useState<string>('META');
  const [symbolInput, setSymbolInput] = useState<string>('META');
  const [expirationDates, setExpirationDates] = useState<number[]>([]);
  const [selectedExpiry, setSelectedExpiry] = useState<number | null>(null);
  const [calls, setCalls] = useState<OptionContract[]>([]);
  const [puts, setPuts] = useState<OptionContract[]>([]);
  const [underlyingPrice, setUnderlyingPrice] = useState<number>(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedContract, setSelectedContract] = useState<OptionContract | null>(null);
  const [contractType, setContractType] = useState<'call' | 'put'>('call');

  async function fetchChain(expiry: number | null, symbolName: string) {
    if (!expiry) return;
    setLoading(true);
    setError(null);
    setSelectedContract(null);

    try {
      const response = await fetch(`${YAHOO_OPTIONS_URL}${symbolName}?date=${expiry}`);
      if (!response.ok) {
        throw new Error(`API returned ${response.status}`);
      }
      const payload = await response.json();
      const optionData = payload?.optionChain?.result?.[0];
      if (!optionData) {
        throw new Error('Option chain response format changed or data is unavailable.');
      }

      setUnderlyingPrice(safeNumber(optionData.quote?.regularMarketPrice));
      setCalls(optionData.options?.[0]?.calls ?? []);
      setPuts(optionData.options?.[0]?.puts ?? []);
      setExpirationDates(optionData.expirationDates ?? []);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    async function loadSymbol() {
      setLoading(true);
      setError(null);
      setSelectedContract(null);
      setSelectedExpiry(null);
      setExpirationDates([]);
      setCalls([]);
      setPuts([]);

      try {
        const response = await fetch(`${YAHOO_OPTIONS_URL}${symbol}`);
        if (!response.ok) {
          throw new Error(`API returned ${response.status}`);
        }
        const payload = await response.json();
        const optionData = payload?.optionChain?.result?.[0];
        if (!optionData) {
          throw new Error('Option chain response format changed or data is unavailable.');
        }
        const expirations = optionData.expirationDates ?? [];
        setExpirationDates(expirations);
        setSelectedExpiry(expirations[0] ?? null);
        setUnderlyingPrice(safeNumber(optionData.quote?.regularMarketPrice));
        setCalls(optionData.options?.[0]?.calls ?? []);
        setPuts(optionData.options?.[0]?.puts ?? []);
      } catch (err) {
        setError((err as Error).message);
      } finally {
        setLoading(false);
      }
    }

    loadSymbol();
  }, [symbol]);

  const handleSymbolSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!symbolInput.trim()) return;
    setSymbol(symbolInput.trim().toUpperCase());
  };

  const handleExpiryChange = async (expiry: number | null) => {
    setSelectedExpiry(expiry);
    if (expiry) {
      await fetchChain(expiry, symbol);
    }
  };

  const bestCalls = useMemo(() => findBestContracts(calls, underlyingPrice, 'call'), [calls, underlyingPrice]);
  const bestPuts = useMemo(() => findBestContracts(puts, underlyingPrice, 'put'), [puts, underlyingPrice]);
  const visibleContracts = contractType === 'call' ? bestCalls : bestPuts;

  const chartData = useMemo(() => {
    if (!selectedContract) return null;
    const series = buildPayoffSeries(selectedContract, underlyingPrice, contractType);
    return {
      labels: series.labels,
      datasets: [
        {
          label: `${contractType.toUpperCase()} payoff for ${selectedContract.contractSymbol}`,
          data: series.values,
          borderColor: 'rgb(37, 99, 235)',
          backgroundColor: 'rgba(37, 99, 235, 0.2)',
          fill: true,
          tension: 0.25
        }
      ]
    };
  }, [selectedContract, underlyingPrice, contractType]);

  return (
    <div className="page-container">
      <header>
        <h1>{symbol} Options Risk vs Reward</h1>
        <p>Fetches option chains, ranks contracts by reward vs premium, and plots payoff curves.</p>
      </header>

      <section className="summary-card">
        <form onSubmit={handleSymbolSubmit} className="symbol-form">
          <label>
            <strong>Symbol:</strong>
            <input
              type="text"
              value={symbolInput}
              onChange={(event: ChangeEvent<HTMLInputElement>) => setSymbolInput(event.target.value)}
              placeholder="Enter ticker symbol"
            />
          </label>
          <button type="submit">Load</button>
        </form>

        <div className="contract-type-toggle">
          <button
            type="button"
            className={contractType === 'call' ? 'active' : ''}
            onClick={() => {
              setContractType('call');
              setSelectedContract(null);
            }}
          >
            Calls
          </button>
          <button
            type="button"
            className={contractType === 'put' ? 'active' : ''}
            onClick={() => {
              setContractType('put');
              setSelectedContract(null);
            }}
          >
            Puts
          </button>
        </div>

        <div><strong>Underlying Price:</strong> {underlyingPrice ? formatCurrency(underlyingPrice) : 'Loading...'}</div>
        <div><strong>Expiry:</strong>
          <select
            value={selectedExpiry ?? ''}
            onChange={(event: ChangeEvent<HTMLSelectElement>) => handleExpiryChange(Number(event.target.value) || null)}
          >
            {expirationDates.map((expiry) => (
              <option key={expiry} value={expiry}>
                {new Date(expiry * 1000).toLocaleDateString('en-US')}
              </option>
            ))}
          </select>
        </div>
      </section>

      {error && <div className="error-banner">Error: {error}</div>}
      {loading && <div className="loading-banner">Loading options data...</div>}

      <section className="list-panel">
        <h2>Top 100 {contractType === 'call' ? 'Call' : 'Put'} candidates</h2>
        <table>
          <thead>
            <tr>
              <th>Strike</th>
              <th>Prem.</th>
              <th>ROI(20%)</th>
              <th>Breakeven</th>
              <th>IV</th>
            </tr>
          </thead>
          <tbody>
            {visibleContracts.map((item) => (
              <tr
                key={item.contract.contractSymbol}
                onClick={() => {
                  setSelectedContract(item.contract);
                  setContractType(contractType);
                }}
              >
                <td>{item.contract.strike}</td>
                <td>{formatCurrency(item.contract.lastPrice)}</td>
                <td>{item.rewardRatio.toFixed(2)}</td>
                <td>{formatCurrency(item.breakeven)}</td>
                <td>{item.contract.impliedVolatility.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {selectedContract && chartData && (
        <section className="chart-panel">
          <div className="chart-header">
            <div>
              <h2>Payoff & Risk/Reward</h2>
              <p>{selectedContract.contractSymbol}</p>
            </div>
            <div className="contract-summary">
              <div><strong>Premium:</strong> {formatCurrency(selectedContract.lastPrice * 100)}</div>
              <div><strong>Strike:</strong> {formatCurrency(selectedContract.strike)}</div>
              <div><strong>Breakeven:</strong> {formatCurrency(contractType === 'call' ? selectedContract.strike + selectedContract.lastPrice : selectedContract.strike - selectedContract.lastPrice)}</div>
            </div>
          </div>
          <Line data={chartData} options={{ responsive: true, plugins: { legend: { position: 'top' }, title: { display: true, text: 'Profit / Loss vs Underlying Price (100 share contract)' } } }} />
        </section>
      )}

      <section className="footer-note">
        <p>Note: This page uses a public Yahoo Finance options endpoint and may require a proxy if CORS blocks the request. It is intended for analysis and not trading advice.</p>
      </section>
    </div>
  );
}
