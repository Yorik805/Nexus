from runtime.registry import PluginRegistry

reg = PluginRegistry()
print('Registered plugins:', reg.list_plugins())
print('Contracts:')
for name, plugin in reg._plugins.items():
    print(f'  {name}: {list(plugin.contracts.keys())}')