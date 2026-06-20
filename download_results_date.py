import requests, os, time, datetime as dt, json, bs4
from pprint import pprint


def get_events(symbol):
    # Request headers



    url = f'https://www.nseindia.com/api/event-calendar?index=equities&symbol={symbol.upper()}'


    try:
        # Making the GET request
        response = requests.get(url, headers=headers)
        
        # Check if the request was successful
        response.raise_for_status()
        
        # Parse and print the JSON response
        data = response.json()
        n = len(data)
        print(f"{symbol} has {n} events")
        return data

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        return None
    except Exception as err:
        print(f"An error occurred: {err}")
        return None

def get_fno_symbols():
  url1 = 'https://www.nseindia.com'
  url2 = 'https://www.nseindia.com/api/underlying-information'


  session = requests.Session()
  headers = {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36',
      'Accept': '*/*',
      'Accept-Language': 'en-US,en;q=0.9',
      'Accept-Encoding': 'gzip, deflate',
      'Connection': 'keep-alive',
      'Referer': 'https://www.nseindia.com',
      'sec-ch_ua_platform': '"Windows"',
      'Sec-Fetch-Site': 'same-origin',
      'Sec-Fetch-Mode': 'cors',
      'Sec-Fetch-Dest': 'empty',
  }
  res1 = session.get(url1, headers=headers)
  print(res1.status_code)
  res2 = session.get(url2, headers=headers, cookies=res1.cookies.get_dict())

  fno_list =  [obj.get("symbol", "") for obj in res2.json().get("data", {}).get("UnderlyingList", []) if obj.get("symbol", "") != ""]

  return fno_list



fno_stocks = get_fno_symbols()

data = {}

for symbol in fno_stocks:
    events = get_events(symbol)
    if events:
        data[symbol] = events
    time.sleep(1)

with open('events.json', 'w') as f:
    f.write(json.dumps(data))