
# Mock Data
branchDevices = {
    'TOKEN_DISPENSER': [{'id': 101}],
    # 'KEYPAD' missing to test resilience
}

mappings = [
    {'source_device_id': 101, 'source_button': 'Button 1', 'target_device_id': 202}
]

def findDeviceById(id):
    for type in branchDevices:
        found = None
        # Simulate JS .find
        for d in branchDevices[type]:
            if d['id'] == id:
                found = d
                break
        if found: return found
    return None

def hydrateCardSelects():
    print("Hydrating...")
    # Simulate finding a mapping that points to a device NOT in branchDevices (e.g. Keypad 202)
    # The logic in mapping.html:
    '''
    const m = mappings.find(mapObj => {
        if (mapObj.source_device_id == sDev && mapObj.source_button == sBtn) {
            const targetDev = findDeviceById(mapObj.target_device_id);
            return targetDev && targetDev.device_type === tType;
        }
        return false;
    });
    '''
    
    # Test case: target device 202 is NOT in branchDevices. findDeviceById returns null.
    targetDev = findDeviceById(202)
    print(f"Target Device 202 found: {targetDev}")
    
    if targetDev is None:
        print("PASS: Handled missing device gracefully (returned None)")
    else:
        print("FAIL: Found non-existent device?")

    # python equivalent of the JS logic check
    sDev = 101
    sBtn = 'Button 1'
    tType = 'KEYPAD'
    
    found_map = None
    for mapObj in mappings:
        if mapObj['source_device_id'] == sDev and mapObj['source_button'] == sBtn:
             tDev = findDeviceById(mapObj['target_device_id'])
             # JS: return targetDev && targetDev.device_type === tType;
             if tDev and tDev.get('device_type') == tType:
                 found_map = mapObj
                 break
    
    print(f"Mapping matching criteria found: {found_map}")

if __name__ == "__main__":
    hydrateCardSelects()
