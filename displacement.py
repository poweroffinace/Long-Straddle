import yfinance as yf
import pandas as pd
import numpy as np 
import os, json, datetime as dt, time, requests, random 

pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)

MAX_DAYS = 5

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
      'sec-ch-ua-platform': '"Windows"',
      'Sec-Fetch-Site': 'same-origin',
      'Sec-Fetch-Mode': 'cors',
      'Sec-Fetch-Dest': 'empty',
  }
  res1 = session.get(url1, headers=headers)
  res2 = session.get(url2, headers=headers, cookies=res1.cookies.get_dict())

  fno_list =  list(filter(lambda symbol : symbol != "", list(map(lambda obj : obj.get("symbol", ""), res2.json().get("data", {}).get("UnderlyingList", [])))))

  return fno_list

fno_stocks = get_fno_symbols()
total_fno_stocks = len(fno_stocks)

print(f"Total fno stocks {len(fno_stocks)}")

# fno_stocks_df = pd.DataFrame(fno_stocks, columns=['symbol'])

# fno_stocks_df['marketCap'] = fno_stocks_df['symbol'].apply(lambda x: yf.Ticker(x + '.NS').info.get('marketCap'))

# fno_stocks_df['marketCap'] = 0

# fno_stocks_df.sort_values(by='marketCap', ascending=True, inplace=True)

# print(fno_stocks_df.to_string())

# idx = random.randint(1, total_fno_stocks-1)

# symbol = fno_stocks_df.iloc[idx]['symbol']


def make_displacement_col(df, days):
    
    df_ = df.copy().iloc[::-1]

    if days != 0:
        df_['high'] = df_.High.rolling(window=days).max()
        df_['low'] = df_.Low.rolling(window=days).min()
    else:
       df_['high'] = df_.High
       df_['low'] = df_.Low

    df_[f"H{days}"] = np.round(df_.high * 100 / df_.Open - 100, 2)
    df_[f"L{days}"] = np.round(100 - df_.low * 100 / df_.Open, 2)
    df[f"D{days}"] = np.maximum(df_[f"H{days}"], df_[f"L{days}"])

    df_ = df_.iloc[::-1]
    return df

def get_displacement_values(symbol):
    price_data_df = yf.download(symbol.upper()+'.NS', period='1y', interval='1d', progress=False, group_by='ticker')[symbol.upper()+'.NS']

    for days in range(0, MAX_DAYS+1):
        price_data_df = make_displacement_col(price_data_df, days)
  
    # print(price_data_df.tail(30).to_string())

    return price_data_df

def get_displacement_dist(price_data_df):
    
    dist_values = {}

    for day in range(0, MAX_DAYS+1):
       dist_values[f"day_{day}"] = {
          'mean'    : float(round(price_data_df[f"D{day}"].mean(), 2)),
          'median'  : float(round(price_data_df[f"D{day}"].median(), 2)),
          'std'     : float(round(price_data_df[f"D{day}"].std(), 2)),
       }
    
    return dist_values


if __name__ == '__main__':

    all_stocks_dis_data = []

    for symbol in fno_stocks[:]:

        print(f'Analysing {symbol}')
        
        df = get_displacement_values(symbol)
        distribution = get_displacement_dist(df)
        # print(distribution)
        all_stocks_dis_data.append({
            'symbol': symbol, 
            'marketCap': yf.Ticker(symbol + '.NS').info.get('marketCap'), 
            'data': distribution
        })

    with open('displacement_data.json', 'w') as f:
        f.write(json.dumps(all_stocks_dis_data))