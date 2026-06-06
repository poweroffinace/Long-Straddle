import json, pandas as pd
from pprint import pprint

MAX_DAYS = 5

with open('displacement_data.json') as f:
    data = json.load(f)

df = []

for item in data:
    symbol = item.get('symbol')
    marketCap = item.get('marketCap')
    
    row = [symbol, marketCap]
    for day in range(1, MAX_DAYS+1):
        mean = item.get('data').get(f'day_{day}').get('mean')
        std  = item.get('data').get(f'day_{day}').get('std')
        row.append(mean)
        row.append(float(round(mean-std, 2)))
    df.append(row)

columns = ['symbol', 'marketCap']
for day in range(1, MAX_DAYS+1):
    columns.append(f'day_{day}')
    columns.append(f'day_{day}_min')
df = pd.DataFrame(df, columns=columns)

df.sort_values(by=['day_1_min', 'day_2_min', 'day_3_min', 'day_4_min', 'day_5_min'], ascending=False, inplace=True)


df.to_csv('displacement_df.csv', index=False)

from nselib import derivatives
lot_size_res = None
def get_lot_size(symbol):
    global lot_size_res
    if lot_size_res is None:
      url = 'https://public.fyers.in/sym_details/NSE_FO.csv'
      df = pd.read_csv(url, header=None)
      lot_size_res = df
      df_symbol = lot_size_res[lot_size_res[13] == symbol]
      lot_sizes = df_symbol[(df_symbol[16] == 'CE') | (df_symbol[16] == 'PE')][3].unique()
      return lot_sizes[0] if len(lot_sizes) > 0 else None
    else:
      df_symbol = lot_size_res[lot_size_res[13] == symbol]
      lot_sizes = df_symbol[(df_symbol[16] == 'CE') | (df_symbol[16] == 'PE')][3].unique()
      return lot_sizes[0] if len(lot_sizes) > 0 else None
    
df = derivatives.nse_live_option_chain(symbol=SYMBOL, expiry_date=EXPIRY)