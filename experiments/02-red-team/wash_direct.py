"""ביקורת ל-A3: חיפוש שממקסם ישירות את רווח ה-wash (תוקף עם ארנק מפסיד, פחות אותו תוקף בלי הארנק), עם ארנקים קטנים."""
import json, random
import redteam as r
TRAIN, TEST = list(range(100, 106)), list(range(500, 530))
mech = r.DEFAULT_MECH
rng = random.Random(11)
space = {'tA': (0, 250), 'd': (1, 20), 'e': (1, 30), 'g': (1, 60), 'bA': (0.2, 5.0), 'bB': (0.2, 5.0)}
def gain(x, seeds):
    a = r.evaluate({'type': 'wash', **x}, mech, seeds)['atk_net']
    c = r.evaluate({'type': 'wash', **dict(x, bB=0.0)}, mech, seeds)['atk_net']
    return a - c
best = None
for i in range(140):
    x = {k: (rng.randint(*v) if isinstance(v[0], int) else rng.uniform(*v)) for k, v in space.items()}
    if best:  # חצי מהמועמדים: שינוי קטן סביב הטוב ביותר
        if i % 2:
            x = {k: (min(v[1], max(v[0], best[1][k] + (rng.randint(-5, 5) if isinstance(v[0], int) else rng.gauss(0, 0.5))))) for k, v in space.items()}
    g = gain(x, TRAIN)
    if best is None or g > best[0]: best = (g, x)
test = gain(best[1], TEST)
out = dict(params=best[1], wash_gain_train=best[0], wash_gain_test=test,
           attacker_capital=best[1]['bA'] + best[1]['bB'])
print(json.dumps(out, ensure_ascii=False))
json.dump(out, open('wash_direct.json', 'w'), ensure_ascii=False, indent=1)
