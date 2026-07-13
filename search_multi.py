import sys, os
from multiprocessing import Pool
from pathlib import Path

def check_file(f):
    try:
        with open(f, 'r', encoding='utf-8') as fd:
            content = fd.read()
            # The serial we are looking for: RA-CH3-LFK-W1-AG08-0000038
            if 'RA-CH3-LFK-W1-AG08-0000038' in content and '12.04' in content:
                return str(f)
    except:
        pass
    return None

if __name__ == '__main__':
    p = Path('D:/BDR/DESTINATION/archive')
    files = list(p.rglob('*.json'))
    with Pool(8) as pool:
        for result in pool.imap_unordered(check_file, files, chunksize=1000):
            if result:
                print(f'MATCH FOUND: {result}')
                sys.exit(0)
    print('No match found.')
