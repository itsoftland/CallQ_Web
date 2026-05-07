
# Simulation of browser environment for createDeviceCard
class MockElement:
    def __init__(self, tag):
        self.tag = tag
        self.className = ""
        self.innerHTML = ""
        self.children = []
        self.style = {}
        self.dataset = {}

    def appendChild(self, child):
        self.children.append(child)
        return child
        
    def querySelector(self, selector):
        if selector == '.dynamic-rows':
            # return a mock element that can accept insertAdjacentHTML
            el = MockElement('div')
            el.className = 'dynamic-rows'
            return el
        return None

    def querySelectorAll(self, selector):
        return []

    def insertAdjacentHTML(self, position, html):
        self.innerHTML += html

document = MockElement('document')
def createElement(tag):
    return MockElement(tag)

document.createElement = createElement

# Mock Data from screenshot: "TD-2026-002 . Device2 . 2 B"
# The UI shows "2 B" which comes from "2_BUTTON".replace('_BUTTON', ' B') in the template.
# So raw token_type is likely "2_BUTTON"

device = {
    'id': 102,
    'get_display_identifier': 'Casuality',
    'device_model': 'Device2',
    'serial_number': 'TD-2026-002',
    'device_type': 'TOKEN_DISPENSER',
    'token_type': '2_BUTTON'
}

# Values for hydration
mappings = []

# functions from mapping.html - EXACT REPLICA
def getButtonsForDevice(device):
    if device['device_type'] == 'TOKEN_DISPENSER':
        # Dynamically get button count from token_type field
        count = 1
        if device.get('token_type'):
            # Format: "1_BUTTON", "2_BUTTON", etc.
            part = device['token_type'].split('_')[0]
            try:
                count = int(part)
            except:
                count = 1
        return [f"Button {i+1}" for i in range(count)]
        
    if device['device_type'] == 'KEYPAD':
        return ['Button A', 'Button B', 'Button C', 'Button D']
        
    return ['Main']

def createMappingRow(sourceId, buttonName, targetType, targetLabel, sourceType):
    return f"<div>Row for {buttonName} -> {targetType}</div>"

def hydrateCardSelects(card):
    pass

# The corrected function to test
def createDeviceCard(device, typeContext):
    col = document.createElement('div');
    col.className = 'col-md-6 col-lg-4'; # Removed fade-in-up

    card = document.createElement('div');
    card.className = 'card h-100 border-0 shadow-sm rounded-4';
    
    # ... header logic ...
    
    # Logic from createDeviceCard
    buttons = getButtonsForDevice(device)
    
    print(f"Device: {device['serial_number']}")
    print(f"Token Type: {device.get('token_type')}")
    print(f"Buttons Found: {buttons}")
    
    if len(buttons) == 0:
        print("FAIL: No buttons generated")
        
    col.appendChild(card)
    return col

if __name__ == "__main__":
    createDeviceCard(device, 'dispenser')
