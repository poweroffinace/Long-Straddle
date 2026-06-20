import requests
import json
import time
from datetime import datetime

url = "https://data.stockmojo.in/simulator/oca"
j = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzZXNzaW9uX3Rva2VuIjoibmhucWN3ZTF3cXN6NHkyYTJlMjE3ODE0MjI2NTQ3NDciLCJ0aWQiOiI4YTg5ZTBmMC04N2U2LTRmM2EtOGYyZC1iNDcxYmY4M2Q5ZTAiLCJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiaWF0IjoxNzgxNDIyNjU0LCJleHAiOjE4MTI5NTg2NTR9.1rtqWOLU5EpzlKW-jh6ohoUdI_nX_eCtMQ8us8ULHAk"
t = "nhnqcwe1wqsz4y2a2e21781422654747"

headers = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "en-US,en;q=0.9",
    "Content-Type": "application/json",
    "Host": "data.stockmojo.in",
    "j": j,
    "Origin": "https://stockmojo.in",
    "sec-ch-ua": '"Chromium";v="148", "Microsoft Edge";v="148", "Not/A)Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "t": t,
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0",
}


def get_data(year, symbol, fixed_month=None, fixed_date=None, fixed_hour=None, fixed_minue=None):
    filename = f"data_{symbol:03d}.json"
    data = {}

    # Helper function to safely reload data from file
    def reload_json_data():
        try:
            with open(filename, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    for month in range(1, 13):
        mm = f"{month:02d}"

        if fixed_month is not None and fixed_month!=month:
            continue

        for date in range(1, 32):
            dd = f"{date:02d}"

            if fixed_date is not None and fixed_date!=date:
                continue

            # Check for valid calendar dates and determine if it's a weekend
            try:
                current_date = datetime(year, month, date)
                # weekday() returns 0 for Monday ... 5 for Saturday, 6 for Sunday
                if current_date.weekday() in [5, 6]:
                    print(f"Skipping {year}-{mm}-{dd} (Weekend)")
                    continue
            except ValueError:
                # Catch invalid dates (e.g., Feb 30th) and skip them
                continue

            for hour in range(9, 16):
                hh = f"{hour:02d}"

                if fixed_hour is not None and fixed_hour!=hour:
                    continue

                # BEFORE STARTING A NEW HOUR: Reload data.json
                data = reload_json_data()

                for minute in range(0, 60, 15):
                    minute_ = minute
                    if hour == 15 and minute_ == 30:
                        minute_ = 29

                    if fixed_minue is not None and fixed_minue!=minute_:
                        continue

                    if hour == 9 and minute_ < 15:
                        continue
                    if hour == 15 and minute_ > 30:
                        continue

                    minu = f"{minute_:02d}"
                        

                    ts = f"{year}-{mm}-{dd} {hh}:{minu}:00"

                    if data.get(ts, []) != []:
                        print(f"{ts} already exists, skip...")
                        continue

                    payload = {"symbol": symbol, "ts": ts}

                    try:
                        response = requests.post(
                            url, headers=headers, json=payload, timeout=10
                        )
                        print(ts, response.status_code, end=" ")
                        if response.status_code == 200:
                            data[ts] = response.json()
                            print(len(data[ts]))
                        else:
                            print(0)
                    except requests.RequestException as e:
                        print(f"Error: {e}")

                    time.sleep(0.5)

                # AFTER EACH DAY COMPLETED: Open data.json and append/save
                # We fetch current file state again to avoid overwriting data saved by concurrent processes if any
                # existing_data = reload_json_data()
                # existing_data.update(data)
                with open(filename, "w") as f:
                    json.dump(data, f, indent=4)
                print(f"--- Day {year}-{mm}-{dd} {hh} completed and saved to {filename} ---")


get_data(2025, 191)
get_data(2025,  95)
get_data(2025,  44)
get_data(2025, 105)
get_data(2025, 195)
get_data(2025, 213)
get_data(2025,  35)
get_data(2025, 141)
get_data(2025, 103)
get_data(2025, 118)
get_data(2025,   1)




# reliance        191
# hdfcbank         95
# bhartiaritel     44
# icicibank       105
# sbin            195
# tcs             213
# bajajfin         35
# lt              141
# hul             103
# infy            118
# nifty50           1

# 11 * 200 * 25 / 3600