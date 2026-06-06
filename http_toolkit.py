import requests, json

url = "https://data.stockmojo.in/simulator/oca"

headers = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "en-US,en;q=0.9",
    "Content-Type": "application/json",
    "Host": "data.stockmojo.in",
    "j": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzZXNzaW9uX3Rva2VuIjoibDNsNGM0MW1lbDhyaHhnc3N6aDE3ODA3MjEyNTE2MzYiLCJ0aWQiOiJiZGI2OGEwMC04M2FkLTQ4MGYtOTdhYS01NmYyMTQ5NmFhNDgiLCJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiaWF0IjoxNzgwNzIxMjUxLCJleHAiOjE4MTIyNTcyNTF9.nOGlqepceD28UjduADpDmFMLlSJ7gqzIsgOK-wqA1eI",
    "Origin": "https://stockmojo.in",
    "sec-ch-ua": '"Chromium";v="148", "Microsoft Edge";v="148", "Not/A)Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "t": "z1iey8w5jsfwzxr8ej51780722990831",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0",
}

payload = {
  "symbol": 1,
  "ts": "2026-06-05 09:17:00"
}  # Add your JSON body here (39 bytes as per Content-Length)

response = requests.post(url, headers=headers, json=payload)

print(response.status_code)
# print(response.json())

with open('response.json', 'w') as f:
    f.write(json.dumps(response.json()))


data = response.json()

spot    = data[0][3]   # 23460.9
vix     = data[1][3]   # 15.62
futures = data[2:5]    # 3 futures rows
options = data[5:]     # all calls and puts

calls = [r for r in options if r[0] == 3]
puts  = [r for r in options if r[0] == 4]

# # Filter by expiry
# weekly_calls = [r for r in calls if r[5] == 193]
# weekly_puts  = [r for r in puts  if r[5] == 193]



# # Each option row: [3/4, lot, oi, ltp, strike, expiry_id, last_trade_ts]
# for c in weekly_calls:
#     print(f"Strike: {c[4]:>6}, LTP: {c[3]:>8}, OI: {c[2]}")


expiries = set([r[5] for r in options])
expiries = sorted(expiries)
print(len(expiries))
print(expiries)


"""
StockMojo Greeks implementation - ported from their exact npm packages:
  black-scholes@1.1.0  (MattL922/black-scholes)
  greeks@1.0.0         (MattL922/greeks)
  implied-volatility@1.0.0 (MattL922/implied-volatility)

These are the exact functions bundled in StockMojo's Next.js chunks.
"""

import math
from datetime import datetime, timezone

# ─────────────────────────────────────────────
# black-scholes.js
# ─────────────────────────────────────────────

def _double_factorial(n):
    """Double factorial: n!! = n * (n-2) * (n-4) * ... """
    val = 1
    i = n
    while i > 1:
        val *= i
        i -= 2
    return val

def std_norm_cdf(x):
    """Standard normal CDF via 100-term series expansion (exactly as in black-scholes.js)"""
    if x >= 8:
        return 1.0
    elif x <= -8:
        return 0.0
    else:
        probability = 0.0
        for i in range(100):
            probability += (x ** (2*i + 1)) / _double_factorial(2*i + 1)
        probability *= math.e ** (-0.5 * x**2)
        probability /= math.sqrt(2 * math.pi)
        probability += 0.5
        return probability

def get_w(s, k, t, v, r):
    """omega (d1) as defined in Black-Scholes"""
    return (r * t + v**2 * t / 2 - math.log(k / s)) / (v * math.sqrt(t))

def black_scholes(s, k, t, v, r, call_put):
    """
    Black-Scholes option price.
    s: spot, k: strike, t: time-to-expiry (years), v: IV (decimal), r: risk-free rate, call_put: 'call'|'put'
    """
    w = get_w(s, k, t, v, r)
    if call_put == "call":
        return s * std_norm_cdf(w) - k * math.e**(-r * t) * std_norm_cdf(w - v * math.sqrt(t))
    else:
        return k * math.e**(-r * t) * std_norm_cdf(v * math.sqrt(t) - w) - s * std_norm_cdf(-w)

# ─────────────────────────────────────────────
# greeks.js
# ─────────────────────────────────────────────

def _std_norm_density(x):
    """Standard normal PDF"""
    return math.e**(-x**2 / 2) / math.sqrt(2 * math.pi)

def get_delta(s, k, t, v, r, call_put):
    w = get_w(s, k, t, v, r)
    if not math.isfinite(w):
        return 1.0 if s > k else 0.0
    delta = std_norm_cdf(w)
    if call_put == "call":
        return delta
    else:
        d = delta - 1
        return 0.0 if (d == -1 and k == s) else d

def get_gamma(s, k, t, v, r):
    w = get_w(s, k, t, v, r)
    return _std_norm_density(w) / (s * v * math.sqrt(t)) if math.isfinite(w) else 0.0

def get_vega(s, k, t, v, r):
    """Vega per 1% move in IV (divided by 100 as in greeks.js)"""
    w = get_w(s, k, t, v, r)
    return (s * math.sqrt(t) * _std_norm_density(w) / 100) if math.isfinite(w) else 0.0

def get_theta(s, k, t, v, r, call_put, scale=365):
    """Theta per calendar day (scale=365 as in greeks.js default)"""
    w = get_w(s, k, t, v, r)
    if not math.isfinite(w):
        return 0.0
    base = -v * s * _std_norm_density(w) / (2 * math.sqrt(t))
    if call_put == "call":
        return (base - k * r * math.e**(-r * t) * std_norm_cdf(w - v * math.sqrt(t))) / scale
    else:
        return (base + k * r * math.e**(-r * t) * std_norm_cdf(v * math.sqrt(t) - w)) / scale

def get_rho(s, k, t, v, r, call_put, scale=100):
    """Rho per 1% move in interest rate (scale=100 as in greeks.js default)"""
    w = get_w(s, k, t, v, r)
    if math.isnan(w):
        return 0.0
    if call_put == "call":
        return k * t * math.e**(-r * t) * std_norm_cdf(w - v * math.sqrt(t)) / scale
    else:
        return -k * t * math.e**(-r * t) * std_norm_cdf(v * math.sqrt(t) - w) / scale

# ─────────────────────────────────────────────
# implied-volatility.js
# ─────────────────────────────────────────────

def get_implied_volatility(expected_cost, s, k, t, r, call_put, estimate=0.1):
    """
    Binary search IV solver - exactly as in implied-volatility.js.
    100 iterations, stops when price matches to the cent.
    """
    low = 0
    high = math.inf
    for _ in range(100):
        actual_cost = black_scholes(s, k, t, estimate, r, call_put)
        # compare price down to the cent (exactly as JS: expectedCost*100 == Math.floor(actualCost*100))
        if int(expected_cost * 100) == math.floor(actual_cost * 100):
            break
        elif actual_cost > expected_cost:
            high = estimate
            estimate = (estimate - low) / 2 + low
        else:
            low = estimate
            estimate = (high - estimate) / 2 + estimate
            if not math.isfinite(estimate):
                estimate = low * 2
    return estimate

# ─────────────────────────────────────────────
# StockMojo helper: compute t from timestamps
# ─────────────────────────────────────────────

def compute_t(current_ts_unix, expiry_ts_unix):
    """
    Time to expiry in years.
    current_ts_unix: unix timestamp of current bar (from last_trade_ts in API or 'ts' param)
    expiry_ts_unix:  unix timestamp of expiry date at 15:30 IST (expiry end of day)
    """
    seconds_left = expiry_ts_unix - current_ts_unix
    return max(seconds_left / (365 * 24 * 3600), 1e-9)


# ─────────────────────────────────────────────
# Full pipeline matching StockMojo's option chain
# ─────────────────────────────────────────────

def compute_greeks_for_option(ltp, spot, strike, current_ts, expiry_ts, call_put, r=0.065):
    """
    Compute IV + all Greeks for a single option row from the StockMojo API.
    
    Parameters:
      ltp         : last traded price (from API row[3])
      spot        : underlying spot price (from API data[0][3])
      strike      : strike price (from API row[4])
      current_ts  : current unix timestamp (from API 'ts' param or row[6])
      expiry_ts   : expiry unix timestamp at 15:30 IST
      call_put    : 'call' or 'put'
      r           : risk-free rate (India ~6.5%)
    
    Returns dict with iv, delta, gamma, theta, vega, rho
    """
    t = compute_t(current_ts, expiry_ts)
    
    try:
        iv = get_implied_volatility(ltp, spot, strike, t, r, call_put)
    except Exception:
        iv = 0.0
    
    if iv <= 0 or not math.isfinite(iv):
        return {"iv": 0, "delta": 0, "gamma": 0, "theta": 0, "vega": 0, "rho": 0}
    
    return {
        "iv":    round(iv * 100, 2),                           # as percentage
        "delta": round(get_delta(spot, strike, t, iv, r, call_put), 4),
        "gamma": round(get_gamma(spot, strike, t, iv, r), 6),
        "theta": round(get_theta(spot, strike, t, iv, r, call_put), 4),  # per day
        "vega":  round(get_vega(spot, strike, t, iv, r), 4),             # per 1% IV move
        "rho":   round(get_rho(spot, strike, t, iv, r, call_put), 4),
    }


# ─────────────────────────────────────────────
# Demo using the sample data from your API response
# ─────────────────────────────────────────────

# if __name__ == "__main__":
#     # From document[2] - sample StockMojo API response
#     # Row format: [type, lot_size, oi, ltp, strike, expiry_id, last_trade_ts]
#     # type: 1=spot, 2=future, 3=call, 4=put
    
#     # Spot price from row[0]
#     # spot = 615.35  # approximate from futures price in doc[2] row[1][3]=605.35
#     spot = data[2][3]

#     # For the actual response you showed - spot would be data[0][3]
#     # Let's use the prices from your sample data
    
#     # The ts param in your request was "2026-06-05 09:17:00" IST
#     # IST = UTC+5:30, so 09:17 IST = 03:47 UTC
#     from datetime import datetime, timezone, timedelta
#     IST = timezone(timedelta(hours=5, minutes=30))
#     current_dt = datetime(2026, 6, 5, 9, 17, 0, tzinfo=IST)
#     current_ts = current_dt.timestamp()
    
#     # expiry_id 42 from sample data - need to map to actual date
#     # Looking at the data, expiry_id=42 corresponds to a near-term expiry
#     # From the footer in HTML: "05 Jun" shown as the futures expiry
#     # So expiry_ts = 2026-06-05 15:30 IST
#     expiry_dt = datetime(2026, 6, 9, 15, 30, 0, tzinfo=IST)
#     expiry_ts = expiry_dt.timestamp()
#     print(expiry_ts)
    
#     t = compute_t(current_ts, expiry_ts)
#     print(f"Time to expiry (years): {t:.6f}")
#     print(f"Time to expiry (hours): {t*365*24:.2f}h\n")
    
#     # Sample call options from the response (type=3)
#     # calls = [
#     #     # [oi, ltp, strike]
#     #     (624750,  22.6,  600),
#     #     (336875,  17.95, 610),
#     #     (1037575, 14.1,  620),
#     #     (1703975, 10.5,  630),
#     #     (2412025, 6.05,  650),
#     # ]
    
#     # # Sample put options from the response (type=4)
#     # puts = [
#     #     (1517775, 16.55, 600),
#     #     (612500,  21.4,  610),
#     #     (766850,  26.3,  620),
#     #     (748475,  33.0,  630),
#     #     (961625,  48.0,  650),
#     # ]
    
#     R = 0.065  # 6.5% risk-free rate for India
    
#     print("=" * 75)
#     print(f"{'CALLS':^75}")
#     print(f"{'Strike':>8} {'LTP':>7} {'IV%':>7} {'Delta':>8} {'Gamma':>9} {'Theta':>8} {'Vega':>8}")
#     print("-" * 75)
#     # call_put_enum, symbol_id, oi, ltp, strike, expiry_id, last_traded_at
#     for oi, ltp, strike in calls:
#         g = compute_greeks_for_option(ltp, spot, strike, current_ts, expiry_ts, "call", R)
#         print(f"{strike:>8} {ltp:>7.2f} {g['iv']:>7.2f} {g['delta']:>8.4f} {g['gamma']:>9.6f} {g['theta']:>8.4f} {g['vega']:>8.4f}")
    
#     print()
#     print("=" * 75)
#     print(f"{'PUTS':^75}")
#     print(f"{'Strike':>8} {'LTP':>7} {'IV%':>7} {'Delta':>8} {'Gamma':>9} {'Theta':>8} {'Vega':>8}")
#     print("-" * 75)
#     for oi, ltp, strike in puts:
#         g = compute_greeks_for_option(ltp, spot, strike, current_ts, expiry_ts, "put", R)
#         print(f"{strike:>8} {ltp:>7.2f} {g['iv']:>7.2f} {g['delta']:>8.4f} {g['gamma']:>9.6f} {g['theta']:>8.4f} {g['vega']:>8.4f}")