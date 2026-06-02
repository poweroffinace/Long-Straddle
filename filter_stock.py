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
        row.append(item.get('data').get(f'day_{day}').get('mean'))
    df.append(row)

columns = ['symbol', 'marketCap']
for day in range(MAX_DAYS+1):
    columns.append(f'day_{day}')
df = pd.DataFrame(df, columns=columns)

df.to_csv('displacement_df.csv', index=False)