import math
import json
from datetime import datetime

# ============================================================
# CONSTANTS (from module 47864)
# ============================================================
INTEREST_RATE = 0.0  # when future exists, else use risk-free rate
# From the code: p(iz,l) ? 0 : e  
# meaning: if future exists → rate=0, else use INTEREST_RATE

# ============================================================
# MODULE 27754 - Core Black-Scholes
# ============================================================

def norm_cdf(x):
    """Approximation of normal CDF (matches JS implementation exactly)"""
    sign = 1 if x >= 0 else -1
    x = abs(x) / math.sqrt(2)
    t = 1 / (1 + 0.3275911 * x)
    result = 1 - (((((1.061405429 * t - 1.453152027) * t + 1.421413741) * t 
                    - 0.284496736) * t + 0.254829592) * t * math.exp(-x * x))
    return 0.5 * (1 + sign * result)

def norm_pdf(x):
    """Standard normal PDF"""
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.PI)

math.PI = math.pi  # alias

def round_with_precision(x, decimals):
    factor = 10 ** decimals
    return round(x * factor) / factor

def price_to_iv(S, K, expiry_ts, r, market_price, option_type, current_ts=None):
    """
    S           = underlying price (future/spot)
    K           = strike
    expiry_ts   = expiry datetime string 'YYYY-MM-DD HH:mm:ss'
    r           = risk-free rate (0 if future exists)
    market_price = option LTP
    option_type = 3 (call/CE) or 4 (put/PE)
    current_ts  = current datetime string (None = now)
    
    Returns implied volatility (not percentage)
    """
    # Time to expiry in years (matches JS: *3168808781402895e-26)
    # 3168808781402895e-26 = 1/(365.25 * 24 * 3600 * 1000) in years per ms
    expiry_dt = datetime.strptime(expiry_ts[:19], '%Y-%m-%d %H:%M:%S')
    
    if current_ts:
        current_dt = datetime.strptime(current_ts[:19], '%Y-%m-%d %H:%M:%S')
    else:
        current_dt = datetime.now()
    
    # Clamp: if current > expiry, use expiry
    if current_dt > expiry_dt:
        current_dt = expiry_dt
    
    # Time in years
    diff_ms = (expiry_dt - current_dt).total_seconds() * 1000
    T = diff_ms * 3.168808781402895e-26  # years
    
    if T <= 0:
        return 0
    
    sqrt_T = math.sqrt(T)
    
    # Intrinsic value floor
    if option_type == 3:  # call
        intrinsic = max(S - K * math.exp(-r * T), 0)
    else:  # put
        intrinsic = max(K * math.exp(-r * T) - S, 0)
    
    if market_price < intrinsic - 1e-8:
        market_price = round_with_precision(intrinsic + 0.01, 2)
    
    # Initial sigma guess
    sigma = min(1, max(0.001, abs(math.log(S / (K * math.exp(-r * T)))) / 10))
    
    # Newton-Raphson
    for _ in range(100):
        d1 = (math.log(S / K) + (r + sigma**2 / 2) * T) / (sigma * sqrt_T)
        d2 = d1 - sigma * sqrt_T
        
        if option_type == 3:
            price = S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)
        else:
            price = K * math.exp(-r * T) * norm_cdf(-d2) - S * norm_cdf(-d1)
        
        diff = price - market_price
        
        if abs(diff) <= 1e-8:
            break
        
        vega = S * norm_pdf(d1) * sqrt_T
        
        if vega < 1e-10:
            # Bisection fallback
            lo, hi = 1e-4, 100
            for _ in range(100):
                sigma = (lo + hi) / 2
                d1 = (math.log(S / K) + (r + sigma**2 / 2) * T) / (sigma * sqrt_T)
                d2 = d1 - sigma * sqrt_T
                if option_type == 3:
                    price = S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)
                else:
                    price = K * math.exp(-r * T) * norm_cdf(-d2) - S * norm_cdf(-d1)
                diff = price - market_price
                if abs(diff) < 1e-8:
                    break
                if price < market_price:
                    lo = sigma
                else:
                    hi = sigma
            break
        
        sigma = max(1e-4, sigma - diff / vega)
    
    return 0 if sigma == 100 else sigma


def greeks_from_iv(S, K, iv, r, option_type, current_ts, expiry_ts, ltp):
    """
    Compute delta, gamma, theta, vega from IV.
    
    Key insight from JS:
    - d1/d2 for delta/gamma uses 'today' (current_ts)  
    - d1/d2 for price/theta uses 'tomorrow' (current_ts + 1 day)
    - theta = -abs(max(ltp - theoretical_price_tomorrow, 0))
    - vega is per 1% move (divided by 100)
    
    option_type: 3=CE, 4=PE
    """
    K = float(K)
    
    expiry_dt  = datetime.strptime(expiry_ts[:19], '%Y-%m-%d %H:%M:%S')
    current_dt = datetime.strptime(current_ts[:19], '%Y-%m-%d %H:%M:%S')
    
    # Clamp current to expiry
    if current_dt > expiry_dt:
        current_dt = expiry_dt
    
    # T for delta/gamma (current → expiry)
    diff_ms = (expiry_dt - current_dt).total_seconds() * 1000
    T = diff_ms * 3.168808781402895e-26
    
    # T for theta (tomorrow → expiry)
    from datetime import timedelta
    tomorrow_dt = current_dt + timedelta(days=1)
    tomorrow_dt = min(tomorrow_dt, expiry_dt)
    diff_ms_tom = (expiry_dt - tomorrow_dt).total_seconds() * 1000
    T_tom = diff_ms_tom * 3.168808781402895e-26
    
    if T <= 0:
        T = 1e-10
    if T_tom <= 0:
        T_tom = 1e-10
    
    # d1, d2 for DELTA/GAMMA (using T)
    d1 = (math.log(S / K) + (r + 0.5 * iv**2) * T) / (iv * math.sqrt(T))
    
    # d1, d2 for PRICE/THETA (using T_tom)
    d1_tom = (math.log(S / K) + (r + 0.5 * iv**2) * T_tom) / (iv * math.sqrt(T_tom))
    d2_tom = d1_tom - iv * math.sqrt(T_tom)
    
    # Theoretical price tomorrow (for theta)
    if option_type == 3:  # CE
        price_tom = S * norm_cdf(d1_tom) - K * math.exp(-r * T_tom) * norm_cdf(d2_tom)
        delta = norm_cdf(d1)
    else:  # PE
        price_tom = K * math.exp(-r * T_tom) * norm_cdf(-d2_tom) - S * norm_cdf(-d1_tom)
        delta = norm_cdf(d1) - 1
    
    # Gamma (same for CE and PE)
    gamma = math.exp(-d1**2 / 2) / (S * iv * math.sqrt(2 * math.pi * T))
    
    # Theta: -abs(max(ltp - theoretical_tomorrow, 0))
    theta = -abs(max(ltp - price_tom, 0))
    
    # Vega: per 1% vol move
    vega = S * math.sqrt(T) * math.exp(-d1**2 / 2) / math.sqrt(2 * math.pi) / 100
    
    return {
        "delta": delta,
        "gamma": gamma,
        "theta": theta,
        "vega": vega
    }


# ============================================================
# MODULE 65474 - getExpiryDate
# ============================================================

def get_expiry_date(id_to_expiry, expiry_key):
    """
    id_to_expiry: dict from /instruments  {expiry_id: [date_str, datetime_str]}
    expiry_key:   the expiry string key
    Returns:      full datetime string 'YYYY-MM-DD HH:mm:ss'
    """
    if id_to_expiry and expiry_key in id_to_expiry:
        entry = id_to_expiry[expiry_key]
        if isinstance(entry, list) and len(entry) > 1:
            return entry[1]  # index [1] is the full datetime
    return f"{expiry_key} 15:29:00"  # fallback


# ============================================================
# MODULE 14630 - priceToCustomIV_d (display IV)
# ============================================================

def time_to_expiry_years(expiry_ts, current_ts):
    """Time difference in years, floored at 0"""
    expiry_dt  = datetime.strptime(expiry_ts[:19], '%Y-%m-%d %H:%M:%S')
    current_dt = datetime.strptime(current_ts[:19], '%Y-%m-%d %H:%M:%S')
    diff_ms = (expiry_dt - current_dt).total_seconds() * 1000
    return max(diff_ms, 0) * 3.168808781402895e-26

def bs_price(S, K, T, r, iv, option_type):
    """Black-Scholes price"""
    if T <= 0:
        if option_type == 'call':
            return max(0, S - K)
        return max(0, K - S)
    discount = math.exp(-r * T)
    if iv == 0:
        if option_type == 'call':
            return max(0, S - K * discount)
        return max(0, K * discount - S)
    d1 = (math.log(S / K) + (r + iv**2 / 2) * T) / (iv * math.sqrt(T))
    d2 = d1 - iv * math.sqrt(T)
    if option_type == 'call':
        return S * norm_cdf(d1) - K * discount * norm_cdf(d2)
    return K * discount * norm_cdf(-d2) - S * norm_cdf(-d1)

def price_to_custom_iv_d(S, K, expiry_ts, r, option_type, current_ts, market_price):
    """
    Display IV (used for iv_d field).
    Uses bisection, returns negative if below intrinsic.
    option_type: 'call' or 'put'
    """
    if current_ts > expiry_ts:
        current_ts = expiry_ts
    
    T = time_to_expiry_years(expiry_ts, current_ts)
    discount = math.exp(-r * T)
    
    if option_type == 'call':
        intrinsic = max(0, S - K * discount)
    else:
        intrinsic = max(0, K * discount - S)
    
    if market_price < intrinsic:
        return (market_price - intrinsic) / 0.01
    
    # Bisection
    lo, hi = 0, 50
    iv = None
    for _ in range(100):
        iv = (lo + hi) / 2
        price = bs_price(S, K, T, r, iv, option_type)
        if abs(price - market_price) < 1e-6:
            break
        if price < market_price:
            lo = iv
        else:
            hi = iv
    
    return iv


# ============================================================
# COMPLETE PIPELINE
# ============================================================

def process_option_chain(raw_data, current_ts, id_to_expiry,
                          expiry_to_id=None, lot_size_map=None):
    """
    raw_data:     API response list of rows
    current_ts:   'YYYY-MM-DD HH:mm:ss'
    id_to_expiry: {symbol_id: {expiry_id_str: [date, datetime]}}
    
    Returns processed dict with spot, vix, futures, options with Greeks
    """
    out = {
        "vix":             {"ltp": None},
        "spot":            {"ltp": 0, "id": 0},
        "future":          {},
        "syntheticFuture": {},
        "option":          {}
    }
    
    # --- Pass 1: spot, vix, futures ---
    for row in raw_data:
        if row[0] == 1:
            if row[1] == 232:
                out["vix"]["ltp"] = row[3]
            elif row[1] < 9:
                out["spot"]["ltp"] = row[3]
            if out["spot"]["id"] == 0 and row[1] != 232:
                out["spot"]["id"] = row[1]
        elif row[0] == 2:
            expiry_key = str(row[5])
            # Resolve expiry_id → date string
            sid = str(out["spot"]["id"])
            date_str = None
            if id_to_expiry and sid in id_to_expiry:
                date_str = id_to_expiry[sid].get(expiry_key)
                if isinstance(date_str, list):
                    date_str = date_str[0]  # use date part
            if date_str is None:
                date_str = expiry_key
            out["future"][date_str] = {
                "ltp": row[3], "oi": row[2], "found": row[6]
            }
    
    # --- Pass 2: options ---
    max_oi = {}
    
    for row in raw_data:
        if row[0] not in (3, 4):
            continue
        
        expiry_key = str(row[5])
        sid = str(out["spot"]["id"])
        
        # Resolve expiry ID → date string
        date_str = None
        if id_to_expiry and sid in id_to_expiry:
            date_str = id_to_expiry[sid].get(expiry_key)
            if isinstance(date_str, list):
                date_str = date_str[0]
        if date_str is None:
            date_str = expiry_key
        
        strike = row[4]
        opt_type = "CE" if row[0] == 3 else "PE"
        ltp = row[3]
        oi = row[2]
        
        # Get underlying price for this expiry
        if date_str in out["future"]:
            S = out["future"][date_str]["ltp"]
            has_future = True
        elif date_str in out["syntheticFuture"]:
            S = out["syntheticFuture"][date_str]["ltp"]
            has_future = False
        else:
            S = out["spot"]["ltp"]
            has_future = False
        
        r = 0 if has_future else INTEREST_RATE
        
        # Get expiry datetime for BS
        expiry_dt_str = get_expiry_date(
            id_to_expiry.get(sid, {}) if id_to_expiry else {},
            expiry_key
        )
        
        # Compute IV
        iv = price_to_iv(S, strike, expiry_dt_str, r, ltp,
                         row[0], current_ts)
        
        iv_d = price_to_custom_iv_d(
            S, strike, expiry_dt_str, r,
            "call" if row[0] == 3 else "put",
            current_ts, ltp
        )
        
        if date_str not in out["option"]:
            out["option"][date_str] = {}
            max_oi[date_str] = 0
        
        if strike not in out["option"][date_str]:
            out["option"][date_str][strike] = {"CE": None, "PE": None}
        
        out["option"][date_str][strike][opt_type] = {
            "ltp":   ltp,
            "oi":    oi,
            "found": row[6],
            "iv":    iv,
            "iv_d":  iv_d
        }
        
        if oi > max_oi[date_str]:
            max_oi[date_str] = oi
    
    # --- Pass 3: compute Greeks for each strike ---
    for expiry, strikes in out["option"].items():
        if expiry in out["future"]:
            S = out["future"][expiry]["ltp"]
            has_future = True
        else:
            S = out["spot"]["ltp"]
            has_future = False
        
        r = 0 if has_future else INTEREST_RATE
        sid = str(out["spot"]["id"])
        expiry_key = str(list(out["option"].keys()).index(expiry))  # fallback
        # Try to find real expiry_key from id_to_expiry
        if expiry_to_id and sid in expiry_to_id:
            expiry_key_real = expiry_to_id[sid].get(expiry)
            if expiry_key_real:
                expiry_key = str(expiry_key_real)
        
        expiry_dt_str = get_expiry_date(
            id_to_expiry.get(sid, {}) if id_to_expiry else {},
            expiry_key
        ) if id_to_expiry else f"{expiry} 15:29:00"
        # Fallback: just use expiry + 15:29:00
        if not expiry_dt_str or expiry_dt_str == f"{expiry_key} 15:29:00":
            expiry_dt_str = f"{expiry} 15:29:00"
        
        for strike, data in strikes.items():
            ce = data.get("CE")
            pe = data.get("PE")
            
            if ce and ce["ltp"] and ce["iv"]:
                g = greeks_from_iv(S, strike, ce["iv"], r, 3,
                                   current_ts, expiry_dt_str, ce["ltp"])
                ce["display"] = {
                    "iv":    round_with_precision(100 * ce["iv"], 1),
                    "delta": round_with_precision(g["delta"], 2),
                    "gamma": round_with_precision(g["gamma"], 4),
                    "theta": round_with_precision(g["theta"], 2),
                    "vega":  round_with_precision(g["vega"], 3),
                }
                # Put delta = call_delta - 1
                if pe:
                    pe["display"] = {**ce["display"]}
                    pe["display"]["delta"] = round_with_precision(g["delta"] - 1, 2)
            
            if pe and pe["ltp"] and pe["iv"] and not (ce and ce.get("display")):
                g = greeks_from_iv(S, strike, pe["iv"], r, 4,
                                   current_ts, expiry_dt_str, pe["ltp"])
                pe["display"] = {
                    "iv":    round_with_precision(100 * pe["iv"], 1),
                    "delta": round_with_precision(g["delta"], 2),
                    "gamma": round_with_precision(g["gamma"], 4),
                    "theta": round_with_precision(g["theta"], 2),
                    "vega":  round_with_precision(g["vega"], 3),
                }
                if ce:
                    ce["display"] = {**pe["display"]}
                    ce["display"]["delta"] = round_with_precision(1 + g["delta"], 2)
    
    return out


# ============================================================
# USAGE EXAMPLE
# ============================================================
if __name__ == "__main__":
    import requests

    BASE = "https://data.stockmojo.in"
    AUTH_HEADERS = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Origin": "https://stockmojo.in",
        "j": "YOUR_JWT",
        "t": "YOUR_SESSION_TOKEN"
    }
    NO_AUTH_HEADERS = {**AUTH_HEADERS, "no_auth": "yes"}

    # Step 1: Get expiry mapping (no auth needed)
    instruments = requests.get(f"{BASE}/instruments",
                               headers=NO_AUTH_HEADERS).json()
    # instruments structure: {'k': {symbol_id: {expiry_id: [date, datetime]}}}
    id_to_expiry   = instruments.get('k', {})
    expiry_to_id   = instruments.get('j', {})  # reverse map
    lot_size_map   = instruments.get('p', {})

    # Step 2: Get option chain
    current_ts = "2026-06-05 09:17:00"
    payload = {"symbol": 1, "ts": current_ts}
    raw = requests.post(f"{BASE}/simulator/oca",
                        headers=AUTH_HEADERS, json=payload).json()

    # Step 3: Process
    result = process_option_chain(
        raw_data=raw,
        current_ts=current_ts,
        id_to_expiry=id_to_expiry,
        expiry_to_id=expiry_to_id,
        lot_size_map=lot_size_map
    )

    print(f"Spot: {result['spot']['ltp']}")
    print(f"VIX:  {result['vix']['ltp']}")

    # Print ATM options for nearest expiry
    for expiry, data in sorted(result["option"].items()):
        spot = result["spot"]["ltp"]
        strikes = sorted(data.keys())
        atm = min(strikes, key=lambda s: abs(s - spot))
        ce = data[atm].get("CE", {})
        pe = data[atm].get("PE", {})
        print(f"\nExpiry: {expiry}, ATM Strike: {atm}")
        if ce and ce.get("display"):
            print(f"  CE LTP={ce['ltp']}, IV={ce['display']['iv']}%,"
                  f" Δ={ce['display']['delta']}, θ={ce['display']['theta']},"
                  f" γ={ce['display']['gamma']}, ν={ce['display']['vega']}")
        if pe and pe.get("display"):
            print(f"  PE LTP={pe['ltp']}, IV={pe['display']['iv']}%,"
                  f" Δ={pe['display']['delta']}, θ={pe['display']['theta']},"
                  f" γ={pe['display']['gamma']}, ν={pe['display']['vega']}")
        break  # just first expiry