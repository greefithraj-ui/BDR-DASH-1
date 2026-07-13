import sys, json, os
from pathlib import Path
sys.path.append('d:/BDR/data')
import api
print('Archive Root:', api._get_archive_root())
