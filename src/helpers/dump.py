import FAPI
scripts = {
    'init': ['Workspace', 'FunnyVM']

}
sdk = FAPI.getSdk()
modulePath = '../FAPI/luau\\'

print(f'dumping {len(scripts)} script(s)')

for fn, path in scripts.items():
    script = sdk.datamodel
    for i in path:
        script = script.findFirstChild(i)
        if script is None:
            print('ERROR: could not find', '.'.join(path), '- are you loaded into the published place?')
            exit(1)
    file = modulePath+fn+'.bin'

    with open(file, 'wb') as f:
        print('Dumping', '.'.join(path), '->', file)
        f.write(script.getAuthenticBytecode())

print("ok")