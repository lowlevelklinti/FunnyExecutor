import FAPI
scripts = {
    'init': ['Workspace', 'ExtractThis']

}
sdk = FAPI.get_sdk()
module_path = '../FAPI/luau\\'

print(f'-- dumping {len(scripts)} script(s) --')

for fn, path in scripts.items():
    script = sdk.datamodel
    for i in path:
        script = script.find_first_child(i)
        if script is None:
            print('ERROR: could not find', '.'.join(path), '- are you loaded into the published place?')
            exit(1)
    file = module_path+fn+'.bin'

    with open(file, 'wb') as f:
        print('Dumping', '.'.join(path), '->', file)
        f.write(script.get_authentic_bytecode())

print("-- finished --")