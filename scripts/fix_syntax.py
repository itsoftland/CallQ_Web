
import os

filepath = '/home/silpc-064/Desktop/CallQ/CallQ/configdetails/templates/configdetails/device_config.html'

print(f"Processing {filepath}...")

with open(filepath, 'r') as f:
    content = f.read()

# Replace occurrences
new_content = content.replace("=='", " == '").replace("'==", "' == ")

if content == new_content:
    print("No changes needed (content already matches).")
else:
    with open(filepath, 'w') as f:
        f.write(new_content)
    print("File updated successfully.")
    
    # Verify specific lines
    with open(filepath, 'r') as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            if i + 1 in [325, 327, 334, 403, 500]: # Check a few known problematic lines
                print(f"Line {i+1}: {line.strip()}")
