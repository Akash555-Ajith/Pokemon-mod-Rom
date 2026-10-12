"""Validate the mod against the original trainer and map data before compiling."""
from pathlib import Path
import json
import re
import subprocess
import sys

root = Path(sys.argv[1])
for name in ('src/data/trainers.h', 'src/data/trainer_parties.h'):
    original = subprocess.check_output(['git', 'show', 'HEAD:' + name], cwd=root)
    assert (root / name).read_bytes().replace(b'\r\n', b'\n') == original.replace(b'\r\n', b'\n'), name
parties = (root / 'src/data/trainer_parties.h').read_text(encoding='utf-8')
leaders = ('Roxanne1', 'Brawly1', 'Wattson1', 'Flannery1', 'Norman1', 'Winona1', 'TateAndLiza1', 'Juan1')
caps = []
for leader in leaders:
    party = re.search(r'sParty_' + leader + r'\[\]\s*=\s*\{(.*?)\n\};', parties, re.S).group(1)
    caps.append(max(map(int, re.findall(r'\.lvl\s*=\s*(\d+)', party))))
implemented = re.search(r'caps\[\]\s*=\s*\{([^}]+)', (root / 'src/nuzlocke.c').read_text()).group(1)
assert caps == list(map(int, re.findall(r'\d+', implemented))), caps
hidden_items = 0
for path in (root / 'data/maps').glob('*/map.json'):
    data = json.loads(path.read_text())
    hidden_items += sum(event.get('type') == 'hidden_item' for event in data.get('bg_events', []))
assert hidden_items > 100
print(f'Original trainers preserved. Verified Gym caps: {caps}. Hidden item events: {hidden_items}.')
