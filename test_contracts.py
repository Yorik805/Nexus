from runtime.registry import PluginRegistry

reg = PluginRegistry()
print('=== Verifying Contracts Match Actual Handlers ===')
print()

# Check memory contracts
mem = reg.get('memory')
print('Memory plugin contracts:')
for action in ['WRITE', 'SEARCH', 'GET', 'DELETE', 'UPDATE', 'LIST']:
    contract = mem.contracts.get(action, {})
    print(f'  {action}: required={list(contract.get("required", {}).keys())}, optional={list(contract.get("optional", {}).keys())}')

print()

# Check terminal contracts
term = reg.get('terminal')
print('Terminal plugin contracts:')
for action in ['EXECUTE', 'STATUS', 'STOP', 'LIST', 'UPDATE', 'CLEANUP']:
    contract = term.contracts.get(action, {})
    print(f'  {action}: required={list(contract.get("required", {}).keys())}, optional={list(contract.get("optional", {}).keys())}')

print()

# Check filesystem contracts
fs = reg.get('filesystem')
print('Filesystem plugin contracts:')
for action in ['READ', 'WRITE', 'APPEND', 'DELETE', 'EXISTS', 'METADATA', 'LIST', 'SEARCH']:
    contract = fs.contracts.get(action, {})
    print(f'  {action}: required={list(contract.get("required", {}).keys())}, optional={list(contract.get("optional", {}).keys())}')

print()

# Check devices contracts
dev = reg.get('devices')
print('Devices plugin contracts:')
for action in ['LIST', 'GET', 'SEND', 'REGISTER', 'DISCONNECT', 'PENDING']:
    contract = dev.contracts.get(action, {})
    print(f'  {action}: required={list(contract.get("required", {}).keys())}, optional={list(contract.get("optional", {}).keys())}')

print()

# Check STT - need to import directly
import importlib
stt = importlib.import_module('plugins.stt.execute')
print('STT plugin contracts:')
for action in ['DETECT_HARDWARE', 'LOAD_MODEL', 'TRANSCRIBE', 'GET_MODEL', 'GET_DEVICE', 'UNLOAD_MODEL']:
    contract = stt._ACTION_CONTRACTS.get(action, {})
    print(f'  {action}: required={list(contract.get("required", {}).keys())}, optional={list(contract.get("optional", {}).keys())}')

print()
print('=== Verification Complete ===')