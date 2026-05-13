#!/usr/bin/env python3
"""
Patch script to add MAC address support to configdetails/views.py.
Run from the CallQ project directory.
"""
import re

filepath = 'configdetails/views.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# ──────────────────────────────────────────────────────────────────
# Patch 1: CSV parsing — add mac_col detection and 3-tuple append
# ──────────────────────────────────────────────────────────────────
old_csv = (
    "sn_col = fieldnames_lower.get('serial number') or fieldnames[0]\n"
    "                     dt_col = fieldnames_lower.get('device type')\n"
    "                     \n"
    "                     for row in csv_reader:\n"
    "                         sn_value = row.get(sn_col, '').strip()\n"
    "                         if sn_value:\n"
    "                             # Get device type from row or default to TV\n"
    "                             device_type = 'TV'\n"
    "                             if dt_col and row.get(dt_col):\n"
    "                                 dt_value = row.get(dt_col, '').strip().upper().replace(' ', '_')\n"
    "                                 # Map common variations\n"
    "                                 dt_mapping = {\n"
    "                                     'TV': 'TV',\n"
    "                                     'TOKEN_DISPENSER': 'TOKEN_DISPENSER',\n"
    "                                     'TOKEN DISPENSER': 'TOKEN_DISPENSER',\n"
    "                                     'TOKENDISPENSER': 'TOKEN_DISPENSER',\n"
    "                                     'KEYPAD': 'KEYPAD',\n"
    "                                     'BROKER': 'BROKER',\n"
    "                                     'LED': 'LED',\n"
    "                                 }\n"
    "                                 device_type = dt_mapping.get(dt_value, 'TV')\n"
    "                             serial_data.append((sn_value, device_type))\n"
    "                             \n"
    "                 elif ext in ['.xlsx', '.xls']:"
)

new_csv = (
    "sn_col = fieldnames_lower.get('serial number') or fieldnames[0]\n"
    "                     dt_col = fieldnames_lower.get('device type')\n"
    "                     mac_col = fieldnames_lower.get('mac address') or fieldnames_lower.get('mac_address')\n"
    "                     \n"
    "                     for row in csv_reader:\n"
    "                         sn_value = row.get(sn_col, '').strip()\n"
    "                         if sn_value:\n"
    "                             # Get device type from row or default to TV\n"
    "                             device_type = 'TV'\n"
    "                             if dt_col and row.get(dt_col):\n"
    "                                 dt_value = row.get(dt_col, '').strip().upper().replace(' ', '_')\n"
    "                                 # Map common variations\n"
    "                                 dt_mapping = {\n"
    "                                     'TV': 'TV',\n"
    "                                     'TOKEN_DISPENSER': 'TOKEN_DISPENSER',\n"
    "                                     'TOKEN DISPENSER': 'TOKEN_DISPENSER',\n"
    "                                     'TOKENDISPENSER': 'TOKEN_DISPENSER',\n"
    "                                     'KEYPAD': 'KEYPAD',\n"
    "                                     'BROKER': 'BROKER',\n"
    "                                     'LED': 'LED',\n"
    "                                 }\n"
    "                                 device_type = dt_mapping.get(dt_value, 'TV')\n"
    "                             # Get optional MAC address\n"
    "                             mac_value = row.get(mac_col, '').strip() if mac_col else ''\n"
    "                             serial_data.append((sn_value, device_type, mac_value or None))\n"
    "                             \n"
    "                 elif ext in ['.xlsx', '.xls']:"
)

if old_csv in content:
    content = content.replace(old_csv, new_csv, 1)
    print("✓ Patch 1 (CSV mac_col) applied")
else:
    print("✗ Patch 1 (CSV mac_col) NOT found — checking with repr...")
    idx = content.find("sn_col = fieldnames_lower.get('serial number')")
    if idx != -1:
        print(repr(content[idx:idx+400]))

# ──────────────────────────────────────────────────────────────────
# Patch 2: XLSX parsing — add mac_idx detection and 3-tuple append
# ──────────────────────────────────────────────────────────────────
old_xlsx = (
    "# Find column indices\n"
    "                     sn_idx = 0\n"
    "                     dt_idx = None\n"
    "                     \n"
    "                     for i, h in enumerate(headers):\n"
    "                         if 'serial' in h and 'number' in h:\n"
    "                             sn_idx = i\n"
    "                         elif 'device' in h and 'type' in h:\n"
    "                             dt_idx = i\n"
    "                     \n"
    "                     # Iterate from second row\n"
    "                     for row in ws.iter_rows(min_row=2, values_only=True):\n"
    "                         if row[sn_idx]:\n"
    "                             sn_value = str(row[sn_idx]).strip()\n"
    "                             device_type = 'TV'\n"
    "                             if dt_idx is not None and row[dt_idx]:\n"
    "                                 dt_value = str(row[dt_idx]).strip().upper().replace(' ', '_')\n"
    "                                 dt_mapping = {\n"
    "                                     'TV': 'TV',\n"
    "                                     'TOKEN_DISPENSER': 'TOKEN_DISPENSER',\n"
    "                                     'TOKEN DISPENSER': 'TOKEN_DISPENSER',\n"
    "                                     'TOKENDISPENSER': 'TOKEN_DISPENSER',\n"
    "                                     'KEYPAD': 'KEYPAD',\n"
    "                                     'BROKER': 'BROKER',\n"
    "                                     'LED': 'LED',\n"
    "                                 }\n"
    "                                 device_type = dt_mapping.get(dt_value, 'TV')\n"
    "                             serial_data.append((sn_value, device_type))\n"
    "                     \n"
    "                 else:"
)

new_xlsx = (
    "# Find column indices\n"
    "                     sn_idx = 0\n"
    "                     dt_idx = None\n"
    "                     mac_idx = None\n"
    "                     \n"
    "                     for i, h in enumerate(headers):\n"
    "                         if 'serial' in h and 'number' in h:\n"
    "                             sn_idx = i\n"
    "                         elif 'device' in h and 'type' in h:\n"
    "                             dt_idx = i\n"
    "                         elif 'mac' in h:\n"
    "                             mac_idx = i\n"
    "                     \n"
    "                     # Iterate from second row\n"
    "                     for row in ws.iter_rows(min_row=2, values_only=True):\n"
    "                         if row[sn_idx]:\n"
    "                             sn_value = str(row[sn_idx]).strip()\n"
    "                             device_type = 'TV'\n"
    "                             if dt_idx is not None and row[dt_idx]:\n"
    "                                 dt_value = str(row[dt_idx]).strip().upper().replace(' ', '_')\n"
    "                                 dt_mapping = {\n"
    "                                     'TV': 'TV',\n"
    "                                     'TOKEN_DISPENSER': 'TOKEN_DISPENSER',\n"
    "                                     'TOKEN DISPENSER': 'TOKEN_DISPENSER',\n"
    "                                     'TOKENDISPENSER': 'TOKEN_DISPENSER',\n"
    "                                     'KEYPAD': 'KEYPAD',\n"
    "                                     'BROKER': 'BROKER',\n"
    "                                     'LED': 'LED',\n"
    "                                 }\n"
    "                                 device_type = dt_mapping.get(dt_value, 'TV')\n"
    "                             # Get optional MAC address\n"
    "                             mac_value = str(row[mac_idx]).strip() if mac_idx is not None and row[mac_idx] else None\n"
    "                             serial_data.append((sn_value, device_type, mac_value))\n"
    "                     \n"
    "                 else:"
)

if old_xlsx in content:
    content = content.replace(old_xlsx, new_xlsx, 1)
    print("✓ Patch 2 (XLSX mac_idx) applied")
else:
    print("✗ Patch 2 (XLSX mac_idx) NOT found")
    idx = content.find("# Find column indices")
    if idx != -1:
        print(repr(content[idx:idx+600]))

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done.")
