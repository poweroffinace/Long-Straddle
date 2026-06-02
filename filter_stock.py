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
    for day in range(MAX_DAYS+1):
        mean = item.get('data').get(f'day_{day}').get('mean')
        std  = item.get('data').get(f'day_{day}').get('std')
        row.append(mean)
        row.append(float(round(mean-std, 2)))
    df.append(row)

columns = ['symbol', 'marketCap']
for day in range(MAX_DAYS+1):
    columns.append(f'day_{day}')
    columns.append(f'day_{day}_min')
df = pd.DataFrame(df, columns=columns)

df.sort_values(by=['day_0', 'day_1', 'day_2', 'day_3', 'day_4', 'day_5'], ascending=False, inplace=True)

df.to_csv('displacement_df.csv', index=False)