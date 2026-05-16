export interface OptionContract {
  contractSymbol: string;
  strike: number;
  lastPrice: number;
  bid: number;
  ask: number;
  change: number;
  percentChange: number;
  volume: number;
  openInterest: number;
  impliedVolatility: number;
  inTheMoney: boolean;
  contractSize: string;
  currency: string;
}

export interface OptionChainResponse {
  underlyingPrice: number;
  expirationDates: number[];
  calls: OptionContract[];
  puts: OptionContract[];
}
