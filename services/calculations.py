import pandas as pd


def calculate_sma(data: pd.Series, window: int = 20) -> pd.Series:
    """
    Simple Moving Average (SMA).

    Args:
        data: Series of prices, e.g. hist['Close'].
        window: Lookback period in bars. Common values: 20, 50, 200.

    Returns:
        Series the same length as `data`. The first `window - 1` values
        are NaN -- there isn't enough history yet to compute them.
    """
    if not isinstance(data, pd.Series):
        raise TypeError("data must be a pandas Series")
    if window < 1:
        raise ValueError("window must be >= 1")

    return data.rolling(window=window, min_periods=window).mean()


def calculate_ema(data: pd.Series, span: int = 20) -> pd.Series:
    """
    Exponential Moving Average (EMA).

    Weights recent prices more heavily than older ones using the
    standard smoothing factor alpha = 2 / (span + 1).

    Args:
        data: Series of prices.
        span: EMA period. Common values: 12 and 26 (MACD legs), 20, 50.

    Returns:
        Series the same length as `data`.
    """
    if not isinstance(data, pd.Series):
        raise TypeError("data must be a pandas Series")
    if span < 1:
        raise ValueError("span must be >= 1")

    return data.ewm(span=span, adjust=False, min_periods=span).mean()


def calculate_rsi(data: pd.Series, window: int = 14) -> pd.Series:
    """
    Relative Strength Index (RSI), using Wilder's smoothing.

    RSI = 100 - (100 / (1 + RS))
    RS  = average gain / average loss over `window` periods, smoothed
    with Wilder's method (equivalent to an EMA with alpha = 1/window).

    This detail matters: Wilder's smoothing is what TradingView,
    Bloomberg and most brokers use. A naive SMA-based RSI will look
    similar but the numbers won't match what your users see elsewhere,
    which erodes trust fast in a finance tool.

    Args:
        data: Series of prices.
        window: Lookback period. 14 is the industry-standard default.

    Returns:
        Series of RSI values in [0, 100], same length as `data`.
        First `window` values are NaN.
    """
    if not isinstance(data, pd.Series):
        raise TypeError("data must be a pandas Series")
    if window < 1:
        raise ValueError("window must be >= 1")

    delta = data.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    # avg_loss == 0 with real gains -> RS is infinite -> RSI should read 100,
    # not NaN/inf. avg_gain == avg_loss == 0 (flat price) -> undefined -> neutral 50.
    rsi = rsi.where(avg_loss != 0, 100)
    rsi = rsi.where(~((avg_gain == 0) & (avg_loss == 0)), 50)

    return rsi


def add_technical_indicators(
    hist: pd.DataFrame,
    sma_window: int = 20,
    ema_span: int = 20,
    rsi_window: int = 14,
) -> pd.DataFrame:
    """
    Convenience wrapper: takes the OHLCV DataFrame from
    services.stock_data.get_historical_data() and returns a copy with
    SMA, EMA and RSI columns appended.

    Usage in app.py:
        hist = get_historical_data(ticker_symbol, period="6mo")
        hist = add_technical_indicators(hist)
        st.line_chart(hist[["Close", "SMA_20", "EMA_20"]])
    """
    if "Close" not in hist.columns:
        raise KeyError("Expected a 'Close' column in the historical data")

    out = hist.copy()
    out[f"SMA_{sma_window}"] = calculate_sma(out["Close"], sma_window)
    out[f"EMA_{ema_span}"] = calculate_ema(out["Close"], ema_span)
    out[f"RSI_{rsi_window}"] = calculate_rsi(out["Close"], rsi_window)
    return out


def get_latest_signal(hist_with_indicators: pd.DataFrame, rsi_window: int = 14) -> dict:
    """
    Reads the most recent row of an indicator-enriched DataFrame and
    returns a simple, human-readable RSI read (Overbought / Oversold /
    Neutral). This is a rule-of-thumb snapshot for display purposes,
    not investment advice.
    """
    rsi_col = f"RSI_{rsi_window}"
    if rsi_col not in hist_with_indicators.columns:
        raise KeyError(f"{rsi_col} not found -- call add_technical_indicators() first")

    latest_rsi = hist_with_indicators[rsi_col].iloc[-1]

    if pd.isna(latest_rsi):
        rsi_read = "Not enough data yet"
    elif latest_rsi >= 70:
        rsi_read = "Overbought"
    elif latest_rsi <= 30:
        rsi_read = "Oversold"
    else:
        rsi_read = "Neutral"

    return {
        "rsi": None if pd.isna(latest_rsi) else round(float(latest_rsi), 2),
        "rsi_signal": rsi_read,
    }