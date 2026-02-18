import datetime
import json

t_delta = datetime.timedelta(hours=9)
JST = datetime.timezone(t_delta, 'JST')
now = datetime.datetime.now(JST)
d = now.strftime('%Y/%m/%d %H:%M:%S')
print(d)

data = {'last_update': d}

with open('src/last_update.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False)
