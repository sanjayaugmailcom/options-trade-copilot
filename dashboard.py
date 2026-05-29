"""
Options Analytics Dashboard — Plotly Dash + TimescaleDB
Run: python dashboard.py  then open http://localhost:8050
"""
import os
import psycopg2
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from dash import Dash, dcc, html, Input, Output, State, callback_context
from dotenv import load_dotenv

load_dotenv()

# ── DB helpers ──────────────────────────────────────────────────────────────

def _conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        dbname=os.getenv("DB_NAME", "options_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "password"),
    )


def qdf(sql, params=None):
    try:
        conn = _conn()
        df = pd.read_sql_query(sql, conn, params=params)
        conn.close()
        return df
    except Exception as exc:
        print(f"[DB error] {exc}")
        return pd.DataFrame()


def get_tickers():
    df = qdf("SELECT DISTINCT ticker FROM options_quotes ORDER BY ticker")
    return df["ticker"].tolist() if not df.empty else []


def get_expirations(ticker):
    df = qdf(
        "SELECT DISTINCT expiration_date FROM options_quotes "
        "WHERE ticker = %s ORDER BY expiration_date",
        [ticker],
    )
    if not df.empty:
        return df["expiration_date"].astype(str).tolist()
    return []


# ── Colour palette ───────────────────────────────────────────────────────────

BG       = "#0d1117"
CARD     = "#161b22"
BORDER   = "#30363d"
BLUE     = "#58a6ff"
GREEN    = "#3fb950"
RED      = "#f85149"
TEXT     = "#e6edf3"
MUTED    = "#8b949e"
YELLOW   = "#d29922"
PURPLE   = "#bc8cff"

PLOTLY_LAYOUT = dict(
    paper_bgcolor=CARD,
    plot_bgcolor=CARD,
    font=dict(color=TEXT, family="Consolas, monospace"),
    xaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER),
    yaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor=BORDER),
    margin=dict(l=50, r=30, t=50, b=50),
)

# ── App ──────────────────────────────────────────────────────────────────────

app = Dash(__name__, title="Options Analytics")

_tickers = get_tickers()
_default_ticker = _tickers[0] if _tickers else None


def _card(children, style=None):
    base = {
        "background": CARD,
        "border": f"1px solid {BORDER}",
        "borderRadius": "8px",
        "padding": "16px",
        "marginBottom": "16px",
    }
    if style:
        base.update(style)
    return html.Div(children, style=base)


def _label(text):
    return html.Label(text, style={"color": MUTED, "fontSize": "12px", "marginBottom": "4px"})


app.layout = html.Div(
    style={"background": BG, "minHeight": "100vh", "fontFamily": "Consolas, monospace", "color": TEXT},
    children=[
        # Header
        html.Div(
            style={"borderBottom": f"1px solid {BORDER}", "padding": "16px 24px", "display": "flex", "alignItems": "center", "gap": "12px"},
            children=[
                html.Span("◈", style={"color": BLUE, "fontSize": "24px"}),
                html.H1("Options Analytics Dashboard", style={"margin": 0, "fontSize": "20px", "color": TEXT}),
                html.Span("TimescaleDB · Plotly Dash", style={"color": MUTED, "fontSize": "13px", "marginLeft": "auto"}),
            ],
        ),

        # Controls
        html.Div(
            style={"padding": "16px 24px", "display": "flex", "gap": "16px", "alignItems": "flex-end", "flexWrap": "wrap"},
            children=[
                html.Div([
                    _label("Ticker"),
                    dcc.Dropdown(
                        id="ticker-dd",
                        options=[{"label": t, "value": t} for t in _tickers],
                        value=_default_ticker,
                        clearable=False,
                        style={"width": "160px", "background": CARD, "color": TEXT},
                    ),
                ]),
                html.Div([
                    _label("Expiration Date"),
                    dcc.Dropdown(
                        id="expiry-dd",
                        options=[],
                        value=None,
                        clearable=False,
                        style={"width": "200px", "background": CARD, "color": TEXT},
                    ),
                ]),
                html.Button(
                    "↻  Refresh",
                    id="refresh-btn",
                    n_clicks=0,
                    style={
                        "background": BLUE,
                        "color": BG,
                        "border": "none",
                        "borderRadius": "6px",
                        "padding": "8px 18px",
                        "cursor": "pointer",
                        "fontFamily": "Consolas, monospace",
                        "fontWeight": "bold",
                        "fontSize": "13px",
                    },
                ),
            ],
        ),

        # Stats bar
        html.Div(id="stats-bar", style={"padding": "0 24px 8px"}),

        # Tabs
        html.Div(
            style={"padding": "0 24px 24px"},
            children=[
                dcc.Tabs(
                    id="tabs",
                    value="chain",
                    style={"borderBottom": f"1px solid {BORDER}"},
                    colors={"border": BORDER, "primary": BLUE, "background": BG},
                    children=[
                        dcc.Tab(label="Chain",            value="chain",   style={"color": MUTED}, selected_style={"color": TEXT, "background": CARD, "borderTop": f"2px solid {BLUE}"}),
                        dcc.Tab(label="IV Analysis",      value="iv",      style={"color": MUTED}, selected_style={"color": TEXT, "background": CARD, "borderTop": f"2px solid {BLUE}"}),
                        dcc.Tab(label="Greeks",           value="greeks",  style={"color": MUTED}, selected_style={"color": TEXT, "background": CARD, "borderTop": f"2px solid {BLUE}"}),
                        dcc.Tab(label="Volume & OI",      value="vol",     style={"color": MUTED}, selected_style={"color": TEXT, "background": CARD, "borderTop": f"2px solid {BLUE}"}),
                        dcc.Tab(label="Liquidity",        value="liq",     style={"color": MUTED}, selected_style={"color": TEXT, "background": CARD, "borderTop": f"2px solid {BLUE}"}),
                        dcc.Tab(label="3D IV Surface",    value="surface", style={"color": MUTED}, selected_style={"color": TEXT, "background": CARD, "borderTop": f"2px solid {BLUE}"}),
                    ],
                ),
                html.Div(id="tab-content", style={"paddingTop": "16px"}),
            ],
        ),
    ],
)


# ── Callbacks ────────────────────────────────────────────────────────────────

@app.callback(
    Output("expiry-dd", "options"),
    Output("expiry-dd", "value"),
    Input("ticker-dd", "value"),
)
def update_expirations(ticker):
    if not ticker:
        return [], None
    exps = get_expirations(ticker)
    opts = [{"label": e, "value": e} for e in exps]
    return opts, (exps[0] if exps else None)


@app.callback(
    Output("stats-bar", "children"),
    Input("ticker-dd", "value"),
    Input("expiry-dd", "value"),
    Input("refresh-btn", "n_clicks"),
)
def update_stats(ticker, expiry, _):
    if not ticker:
        return []

    df = qdf(
        """
        SELECT
            COUNT(*) AS total_quotes,
            COUNT(DISTINCT expiration_date) AS unique_expirations,
            COUNT(DISTINCT strike) AS unique_strikes,
            MIN(time) AS first_quote,
            MAX(time) AS last_quote
        FROM options_quotes WHERE ticker = %s
        """,
        [ticker],
    )

    if df.empty or df["total_quotes"].iloc[0] == 0:
        return _card(html.Span("No data found for this ticker.", style={"color": MUTED}))

    r = df.iloc[0]
    first = str(r["first_quote"])[:16] if r["first_quote"] else "—"
    last  = str(r["last_quote"])[:16]  if r["last_quote"]  else "—"

    def stat(label, value, color=TEXT):
        return html.Div(
            [
                html.Div(str(value), style={"fontSize": "22px", "color": color, "fontWeight": "bold"}),
                html.Div(label, style={"fontSize": "11px", "color": MUTED}),
            ],
            style={"textAlign": "center", "minWidth": "120px"},
        )

    return _card(
        html.Div(
            [
                stat("Total Quotes",    f"{int(r['total_quotes']):,}", BLUE),
                html.Div(style={"width": "1px", "background": BORDER, "margin": "0 16px"}),
                stat("Expirations",     int(r["unique_expirations"]), YELLOW),
                stat("Unique Strikes",  int(r["unique_strikes"]), PURPLE),
                html.Div(style={"width": "1px", "background": BORDER, "margin": "0 16px"}),
                stat("First Quote",     first, MUTED),
                stat("Last Quote",      last,  MUTED),
            ],
            style={"display": "flex", "gap": "24px", "alignItems": "center"},
        )
    )


@app.callback(
    Output("tab-content", "children"),
    Input("tabs", "value"),
    Input("ticker-dd", "value"),
    Input("expiry-dd", "value"),
    Input("refresh-btn", "n_clicks"),
)
def render_tab(tab, ticker, expiry, _):
    if not ticker or not expiry:
        return html.Div("Select a ticker and expiration date.", style={"color": MUTED, "padding": "40px", "textAlign": "center"})

    if tab == "chain":
        return tab_chain(ticker, expiry)
    if tab == "iv":
        return tab_iv(ticker, expiry)
    if tab == "greeks":
        return tab_greeks(ticker, expiry)
    if tab == "vol":
        return tab_volume(ticker, expiry)
    if tab == "liq":
        return tab_liquidity(ticker, expiry)
    if tab == "surface":
        return tab_surface(ticker)
    return html.Div("Unknown tab")


# ── Tab builders ─────────────────────────────────────────────────────────────

def _empty_fig(msg="No data available"):
    fig = go.Figure()
    fig.update_layout(**PLOTLY_LAYOUT, annotations=[dict(text=msg, x=0.5, y=0.5, showarrow=False, font=dict(color=MUTED, size=14))])
    return fig


def tab_chain(ticker, expiry):
    """Options chain table — ATM at top, ITM highlighted, sorted by proximity to current price."""
    df = qdf(
        """
        SELECT DISTINCT ON (strike, option_type)
            strike, option_type, last, iv, delta, gamma, theta, vega, volume, open_interest
        FROM options_quotes
        WHERE ticker = %s AND expiration_date = %s
        ORDER BY strike, option_type, time DESC
        """,
        [ticker, expiry],
    )

    if df.empty:
        return _card(dcc.Graph(figure=_empty_fig("No chain data for this expiration"), config={"displayModeBar": False}))

    df["strike"] = df["strike"].astype(float)
    calls = df[df["option_type"] == "C"].drop("option_type", axis=1).set_index("strike")
    puts  = df[df["option_type"] == "P"].drop("option_type", axis=1).set_index("strike")

    all_strikes = sorted(set(calls.index.tolist()) | set(puts.index.tolist()))

    # Estimate current price: call strike with delta closest to 0.5
    atm_strike = None
    c_valid = calls[calls["delta"].notna()]
    if not c_valid.empty:
        atm_strike = float((c_valid["delta"] - 0.5).abs().idxmin())

    # Sort closest-to-ATM first
    if atm_strike is not None:
        all_strikes.sort(key=lambda s: abs(s - atm_strike))

    n = len(all_strikes)

    def _v(frame, strike, col):
        try:
            v = frame.at[strike, col]
            return None if pd.isna(v) else v
        except (KeyError, TypeError):
            return None

    def f2(v):    return f"{v:.2f}"       if v is not None else "—"
    def f3(v):    return f"{v:.3f}"       if v is not None else "—"
    def fpct(v):  return f"{v*100:.1f}%"  if v is not None else "—"
    def fint(v):  return f"{int(v):,}"    if v is not None and float(v) > 0 else "—"

    c_oi    = [fint(_v(calls, s, "open_interest")) for s in all_strikes]
    c_vol   = [fint(_v(calls, s, "volume"))        for s in all_strikes]
    c_last  = [f2  (_v(calls, s, "last"))          for s in all_strikes]
    c_iv    = [fpct(_v(calls, s, "iv"))            for s in all_strikes]
    c_delta = [f3  (_v(calls, s, "delta"))         for s in all_strikes]
    c_gamma = [f3  (_v(calls, s, "gamma"))         for s in all_strikes]
    s_vals  = [f"${s:,.2f}" for s in all_strikes]
    p_gamma = [f3  (_v(puts,  s, "gamma"))         for s in all_strikes]
    p_delta = [f3  (_v(puts,  s, "delta"))         for s in all_strikes]
    p_iv    = [fpct(_v(puts,  s, "iv"))            for s in all_strikes]
    p_last  = [f2  (_v(puts,  s, "last"))          for s in all_strikes]
    p_vol   = [fint(_v(puts,  s, "volume"))        for s in all_strikes]
    p_oi    = [fint(_v(puts,  s, "open_interest")) for s in all_strikes]

    # Colour bands: ATM=blue, ITM call=green, ITM put=red
    atm_tol = (atm_strike * 0.005) if atm_strike else 0  # ±0.5% of spot

    def mk_colors(side):
        out = []
        for s in all_strikes:
            if atm_strike and abs(s - atm_strike) <= atm_tol:
                out.append("rgba(88,166,255,0.22)")
            elif side == "call" and atm_strike and s < atm_strike:
                out.append("rgba(63,185,80,0.10)")
            elif side == "put"  and atm_strike and s > atm_strike:
                out.append("rgba(248,81,73,0.10)")
            else:
                out.append(CARD)
        return out

    cc = mk_colors("call")
    pc = mk_colors("put")
    sc = [
        "rgba(88,166,255,0.35)" if atm_strike and abs(s - atm_strike) <= atm_tol else CARD
        for s in all_strikes
    ]

    spot_txt = f"  (est. spot ~${atm_strike:,.2f})" if atm_strike else ""

    fig = go.Figure(go.Table(
        columnwidth=[50, 50, 55, 50, 45, 45,  70,  45, 45, 50, 55, 50, 50],
        header=dict(
            values=["OI", "Vol", "Last", "IV", "Gamma", "Delta",
                    "Strike",
                    "Delta", "Gamma", "IV", "Last", "Vol", "OI"],
            fill_color=[BORDER]*6 + ["rgba(88,166,255,0.3)"] + [BORDER]*6,
            font=dict(
                color=[GREEN]*6 + [TEXT] + [RED]*6,
                size=12, family="Consolas, monospace",
            ),
            align="center",
            line_color=BORDER,
            height=30,
        ),
        cells=dict(
            values=[c_oi, c_vol, c_last, c_iv, c_gamma, c_delta,
                    s_vals,
                    p_delta, p_gamma, p_iv, p_last, p_vol, p_oi],
            fill_color=[cc, cc, cc, cc, cc, cc,  sc,  pc, pc, pc, pc, pc, pc],
            font=dict(color=TEXT, size=11, family="Consolas, monospace"),
            align=["right"]*6 + ["center"] + ["right"]*6,
            line_color=BORDER,
            height=23,
        ),
    ))

    fig.update_layout(
        paper_bgcolor=CARD,
        font=dict(color=TEXT, family="Consolas, monospace"),
        title=dict(
            text=f"CALLS  |  {ticker} Options Chain  |  {expiry}{spot_txt}  |  PUTS",
            font=dict(color=TEXT, size=14),
            x=0.5, xanchor="center",
        ),
        height=max(500, min(1400, n * 24 + 130)),
        margin=dict(l=5, r=5, t=65, b=5),
    )

    return _card(dcc.Graph(figure=fig, config={"displayModeBar": True}))


def tab_iv(ticker, expiry):
    """IV Smile + IV Term Structure"""

    # --- IV Smile ---
    df_smile = qdf(
        """
        SELECT strike, option_type, AVG(iv) AS avg_iv, MIN(iv) AS min_iv, MAX(iv) AS max_iv
        FROM options_quotes
        WHERE ticker = %s AND expiration_date = %s AND iv IS NOT NULL AND iv > 0
        GROUP BY strike, option_type ORDER BY strike
        """,
        [ticker, expiry],
    )

    fig_smile = go.Figure()
    if not df_smile.empty:
        for opt_type, color, name in [("C", GREEN, "Calls"), ("P", RED, "Puts")]:
            sub = df_smile[df_smile["option_type"] == opt_type]
            if sub.empty:
                continue
            fig_smile.add_trace(go.Scatter(
                x=sub["strike"], y=(sub["avg_iv"] * 100).round(2),
                mode="lines+markers", name=name,
                line=dict(color=color, width=2),
                marker=dict(size=5),
                error_y=dict(
                    type="data",
                    array=((sub["max_iv"] - sub["avg_iv"]) * 100).tolist(),
                    arrayminus=((sub["avg_iv"] - sub["min_iv"]) * 100).tolist(),
                    visible=True, thickness=1, color=color,
                ),
            ))
        fig_smile.update_layout(
            **PLOTLY_LAYOUT,
            title=dict(text=f"{ticker} IV Smile — Exp {expiry}", font=dict(color=TEXT)),
            xaxis_title="Strike",
            yaxis_title="Implied Volatility (%)",
        )
    else:
        fig_smile = _empty_fig("No IV data for this expiration")

    # --- IV Term Structure ---
    df_term = qdf(
        """
        SELECT
            expiration_date,
            EXTRACT(DAY FROM expiration_date::date - CURRENT_DATE)::int AS dte,
            AVG(iv) AS avg_iv, MIN(iv) AS min_iv, MAX(iv) AS max_iv
        FROM options_quotes
        WHERE ticker = %s AND iv IS NOT NULL AND iv > 0
        GROUP BY expiration_date ORDER BY expiration_date
        """,
        [ticker],
    )

    fig_term = go.Figure()
    if not df_term.empty:
        fig_term.add_trace(go.Scatter(
            x=df_term["dte"], y=(df_term["avg_iv"] * 100).round(2),
            mode="lines+markers",
            line=dict(color=BLUE, width=2),
            marker=dict(size=7, color=BLUE),
            fill="tozeroy", fillcolor="rgba(88,166,255,0.08)",
            name="Avg IV",
            text=df_term["expiration_date"].astype(str),
            hovertemplate="DTE: %{x}<br>IV: %{y:.1f}%<br>Expiry: %{text}<extra></extra>",
        ))
        # Mark selected expiry
        sel = df_term[df_term["expiration_date"].astype(str) == expiry]
        if not sel.empty:
            fig_term.add_trace(go.Scatter(
                x=sel["dte"], y=(sel["avg_iv"] * 100).round(2),
                mode="markers", name="Selected",
                marker=dict(size=12, color=YELLOW, symbol="star"),
            ))
        fig_term.update_layout(
            **PLOTLY_LAYOUT,
            title=dict(text=f"{ticker} IV Term Structure", font=dict(color=TEXT)),
            xaxis_title="Days to Expiration",
            yaxis_title="Avg Implied Volatility (%)",
        )
    else:
        fig_term = _empty_fig("No IV term structure data")

    return html.Div([
        _card(dcc.Graph(figure=fig_smile, config={"displayModeBar": True})),
        _card(dcc.Graph(figure=fig_term,  config={"displayModeBar": True})),
    ])


def tab_greeks(ticker, expiry):
    """Delta, Gamma, Theta, Vega by strike"""
    df = qdf(
        """
        SELECT DISTINCT ON (strike, option_type)
            strike, option_type, delta, gamma, theta, vega, rho
        FROM options_quotes
        WHERE ticker = %s AND expiration_date = %s AND delta IS NOT NULL
        ORDER BY strike, option_type, time DESC
        """,
        [ticker, expiry],
    )

    if df.empty:
        return _card(dcc.Graph(figure=_empty_fig("No Greeks data for this expiration"), config={"displayModeBar": False}))

    greeks = [
        ("delta", "Delta",  BLUE),
        ("gamma", "Gamma",  GREEN),
        ("theta", "Theta",  RED),
        ("vega",  "Vega",   YELLOW),
    ]

    figs = []
    for col, label, color in greeks:
        if col not in df.columns:
            continue
        fig = go.Figure()
        for opt_type, line_dash, name in [("C", "solid", "Calls"), ("P", "dash", "Puts")]:
            sub = df[df["option_type"] == opt_type].dropna(subset=[col]).sort_values("strike")
            if sub.empty:
                continue
            fig.add_trace(go.Scatter(
                x=sub["strike"], y=sub[col].round(6),
                mode="lines+markers", name=name,
                line=dict(color=color, width=2, dash=line_dash),
                marker=dict(size=4),
            ))
        fig.update_layout(
            **PLOTLY_LAYOUT,
            title=dict(text=f"{label} by Strike", font=dict(color=TEXT, size=14)),
            xaxis_title="Strike",
            yaxis_title=label,
            height=280,
        )
        figs.append(dcc.Graph(figure=fig, config={"displayModeBar": False}))

    # 2×2 grid
    rows = [
        html.Div(figs[i : i + 2], style={"display": "flex", "gap": "16px"})
        for i in range(0, len(figs), 2)
    ]
    return _card(html.Div([
        html.H3(f"Greeks Distribution — {ticker} exp {expiry}", style={"color": MUTED, "margin": "0 0 12px", "fontSize": "14px"}),
        *rows,
    ]))


def tab_volume(ticker, expiry):
    """Volume & Open Interest by strike"""
    df = qdf(
        """
        SELECT strike, option_type,
               SUM(volume)        AS total_volume,
               MAX(open_interest) AS open_interest
        FROM options_quotes
        WHERE ticker = %s AND expiration_date = %s
        GROUP BY strike, option_type ORDER BY strike
        """,
        [ticker, expiry],
    )

    if df.empty:
        return _card(dcc.Graph(figure=_empty_fig("No volume data"), config={"displayModeBar": False}))

    calls = df[df["option_type"] == "C"]
    puts  = df[df["option_type"] == "P"]

    # Volume chart
    fig_vol = go.Figure()
    if not calls.empty:
        fig_vol.add_trace(go.Bar(x=calls["strike"], y=calls["total_volume"], name="Call Volume", marker_color=GREEN, opacity=0.85))
    if not puts.empty:
        fig_vol.add_trace(go.Bar(x=puts["strike"], y=-puts["total_volume"].abs(), name="Put Volume", marker_color=RED, opacity=0.85))
    fig_vol.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text=f"{ticker} Volume by Strike — Exp {expiry}", font=dict(color=TEXT)),
        xaxis_title="Strike", yaxis_title="Volume (Calls ↑  Puts ↓)",
        barmode="overlay",
    )

    # OI chart
    fig_oi = go.Figure()
    if not calls.empty:
        fig_oi.add_trace(go.Bar(x=calls["strike"], y=calls["open_interest"], name="Call OI", marker_color=GREEN, opacity=0.85))
    if not puts.empty:
        fig_oi.add_trace(go.Bar(x=puts["strike"], y=-puts["open_interest"].abs(), name="Put OI", marker_color=RED, opacity=0.85))
    fig_oi.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text=f"{ticker} Open Interest by Strike — Exp {expiry}", font=dict(color=TEXT)),
        xaxis_title="Strike", yaxis_title="OI (Calls ↑  Puts ↓)",
        barmode="overlay",
    )

    # Put/Call ratio gauges
    c_vol = int(calls["total_volume"].sum()) if not calls.empty else 0
    p_vol = int(puts["total_volume"].sum())  if not puts.empty  else 0
    c_oi  = int(calls["open_interest"].sum()) if not calls.empty else 0
    p_oi  = int(puts["open_interest"].sum())  if not puts.empty  else 0
    pcr_vol = p_vol / c_vol if c_vol else 0
    pcr_oi  = p_oi  / c_oi  if c_oi  else 0

    def gauge(title, value, max_val=2.0):
        color = GREEN if value < 0.8 else (YELLOW if value < 1.2 else RED)
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=round(value, 3),
            title={"text": title, "font": {"color": MUTED, "size": 13}},
            number={"font": {"color": color, "size": 24}},
            gauge={
                "axis": {"range": [0, max_val], "tickcolor": MUTED},
                "bar": {"color": color},
                "bgcolor": CARD,
                "bordercolor": BORDER,
                "steps": [
                    {"range": [0, 0.8],      "color": "rgba(63,185,80,0.12)"},
                    {"range": [0.8, 1.2],    "color": "rgba(210,153,34,0.12)"},
                    {"range": [1.2, max_val], "color": "rgba(248,81,73,0.12)"},
                ],
            },
        ))
        fig.update_layout(paper_bgcolor=CARD, font=dict(color=TEXT), height=220, margin=dict(l=20, r=20, t=40, b=10))
        return fig

    return html.Div([
        _card(dcc.Graph(figure=fig_vol, config={"displayModeBar": True})),
        _card(dcc.Graph(figure=fig_oi,  config={"displayModeBar": True})),
        html.Div([
            _card(dcc.Graph(figure=gauge("Put/Call Volume Ratio", pcr_vol), config={"displayModeBar": False}), style={"flex": "1"}),
            _card(dcc.Graph(figure=gauge("Put/Call OI Ratio", pcr_oi),      config={"displayModeBar": False}), style={"flex": "1"}),
        ], style={"display": "flex", "gap": "16px"}),
    ])


def tab_liquidity(ticker, expiry):
    """Liquidity analysis — volume, open interest, OI/volume ratio (bid/ask not in API)"""
    df = qdf(
        """
        SELECT DISTINCT ON (strike, option_type)
            strike, option_type, last, volume, open_interest,
            CASE WHEN volume > 0 THEN open_interest::float / volume END AS oi_vol_ratio
        FROM options_quotes
        WHERE ticker = %s AND expiration_date = %s
        ORDER BY strike, option_type, time DESC
        """,
        [ticker, expiry],
    )

    if df.empty:
        return _card(dcc.Graph(figure=_empty_fig("No data for this expiration"), config={"displayModeBar": False}))

    calls = df[df["option_type"] == "C"].sort_values("strike")
    puts  = df[df["option_type"] == "P"].sort_values("strike")

    # Last price by strike
    fig_last = go.Figure()
    for sub, color, name in [(calls, GREEN, "Calls"), (puts, RED, "Puts")]:
        s = sub.dropna(subset=["last"])
        if not s.empty:
            fig_last.add_trace(go.Scatter(
                x=s["strike"], y=s["last"].round(4),
                mode="lines+markers", name=name,
                line=dict(color=color, width=2), marker=dict(size=5),
            ))
    fig_last.update_layout(**PLOTLY_LAYOUT,
        title=dict(text=f"{ticker} Last Price by Strike — Exp {expiry}", font=dict(color=TEXT)),
        xaxis_title="Strike", yaxis_title="Last Price ($)")

    # OI/Volume ratio — high ratio = stale positioning, low = fresh activity
    fig_ratio = go.Figure()
    for sub, color, name in [(calls, GREEN, "Calls"), (puts, RED, "Puts")]:
        s = sub.dropna(subset=["oi_vol_ratio"])
        if not s.empty:
            fig_ratio.add_trace(go.Bar(
                x=s["strike"], y=s["oi_vol_ratio"].round(1),
                name=name, marker_color=color, opacity=0.8,
            ))
    fig_ratio.update_layout(**PLOTLY_LAYOUT, barmode="group",
        title=dict(text="OI / Volume Ratio by Strike  (high = stale positions, low = fresh activity)", font=dict(color=TEXT, size=13)),
        xaxis_title="Strike", yaxis_title="OI ÷ Volume")

    # Volume + OI side-by-side scatter for active strikes
    fig_activity = go.Figure()
    for sub, marker_color, name in [(calls, GREEN, "Calls"), (puts, RED, "Puts")]:
        s = sub.dropna(subset=["volume", "open_interest"])
        if not s.empty:
            fig_activity.add_trace(go.Scatter(
                x=s["volume"], y=s["open_interest"],
                mode="markers", name=name,
                marker=dict(color=marker_color, size=8, opacity=0.8),
                text=s["strike"].astype(str),
                hovertemplate="Strike %{text}<br>Vol: %{x:,}<br>OI: %{y:,}<extra></extra>",
            ))
    fig_activity.update_layout(**PLOTLY_LAYOUT,
        title=dict(text="Volume vs Open Interest per Strike  (bubble = strike)", font=dict(color=TEXT)),
        xaxis_title="Volume (today)", yaxis_title="Open Interest")

    return html.Div([
        _card(dcc.Graph(figure=fig_last,     config={"displayModeBar": True})),
        html.Div([
            _card(dcc.Graph(figure=fig_ratio,    config={"displayModeBar": True}), style={"flex": "1"}),
            _card(dcc.Graph(figure=fig_activity, config={"displayModeBar": True}), style={"flex": "1"}),
        ], style={"display": "flex", "gap": "16px"}),
    ])


def tab_surface(ticker):
    """3D IV Surface: Strike × Expiration × IV"""
    df = qdf(
        """
        SELECT
            strike,
            expiration_date,
            EXTRACT(DAY FROM expiration_date::date - CURRENT_DATE)::int AS dte,
            AVG(iv) AS avg_iv
        FROM options_quotes
        WHERE ticker = %s AND iv IS NOT NULL AND iv > 0
        GROUP BY strike, expiration_date
        ORDER BY expiration_date, strike
        """,
        [ticker],
    )

    if df.empty or df["avg_iv"].isna().all():
        return _card(dcc.Graph(figure=_empty_fig("Not enough data for IV surface (need multiple expirations)"), config={"displayModeBar": False}))

    # Pivot to matrix: rows = strikes, cols = expirations (by DTE)
    pivot = df.pivot_table(index="strike", columns="dte", values="avg_iv", aggfunc="mean")
    pivot = pivot.sort_index()

    strikes = pivot.index.values.astype(float)
    dtes    = pivot.columns.values.astype(float)
    z_vals  = (pivot.values * 100).round(2)   # convert to %

    # Replace NaN with interpolated where possible, leave as NaN otherwise (Plotly handles it)
    fig = go.Figure(go.Surface(
        x=dtes,
        y=strikes,
        z=z_vals,
        colorscale=[
            [0.0,  "rgb(13,17,23)"],
            [0.25, "rgb(0,90,180)"],
            [0.5,  "rgb(0,180,120)"],
            [0.75, "rgb(210,153,34)"],
            [1.0,  "rgb(248,81,73)"],
        ],
        colorbar=dict(title="IV (%)", tickfont=dict(color=TEXT), titlefont=dict(color=TEXT)),
        hovertemplate="DTE: %{x}<br>Strike: %{y}<br>IV: %{z:.1f}%<extra></extra>",
        contours=dict(
            z=dict(show=True, usecolormap=True, highlightcolor=TEXT, project=dict(z=True)),
        ),
    ))

    fig.update_layout(
        paper_bgcolor=CARD,
        scene=dict(
            bgcolor=CARD,
            xaxis=dict(title="Days to Expiry", gridcolor=BORDER, color=TEXT),
            yaxis=dict(title="Strike",         gridcolor=BORDER, color=TEXT),
            zaxis=dict(title="IV (%)",         gridcolor=BORDER, color=TEXT),
        ),
        font=dict(color=TEXT, family="Consolas, monospace"),
        title=dict(text=f"{ticker} Implied Volatility Surface", font=dict(color=TEXT, size=16)),
        margin=dict(l=0, r=0, t=50, b=0),
        height=620,
    )

    return _card(dcc.Graph(figure=fig, config={"displayModeBar": True}))


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Starting Options Analytics Dashboard…")
    print("Open http://localhost:8050 in your browser\n")
    app.run(debug=True, host="0.0.0.0", port=8050)
