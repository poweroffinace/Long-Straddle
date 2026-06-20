import json 

with open('data_191.json', 'r') as f:
    data = f.read()

data = json.loads(data)

for k, v in data.items():
    print(f"{k} : {len(v)}")