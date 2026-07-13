import ast
with open('D:/BDR/data/api.py', 'r') as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if '_calc_avg_bdr' in line:
        print(f'{i+1}: {line.strip()}')
