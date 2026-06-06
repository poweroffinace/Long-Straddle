import requests
import json
import time
from datetime import datetime

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


def get_data(year, symbol):
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

        for date in range(1, 32):
            dd = f"{date:02d}"

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

                # BEFORE STARTING A NEW HOUR: Reload data.json
                data = reload_json_data()

                for minute in range(0, 60):
                    if hour == 9 and minute < 15:
                        continue
                    if hour == 15 and minute > 30:
                        continue

                    minu = f"{minute:02d}"
                    ts = f"{year}-{mm}-{dd} {hh}:{minu}:00"
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
            print(f"--- Day {year}-{mm}-{dd} completed and saved to {filename} ---")


get_data(2025, 1)
