import json
import os.path
import requests
import traceback
from pathlib import Path

appData = Path(os.environ['APPDATA']+'\\FunnyExecutor')
offsetsToCopy = {
    "fake_datamodel_ptr": ["FakeDataModel", "Pointer"],
    "real_datamodel_ptr": ["FakeDataModel", "RealDataModel"],
    "ins_name": ["Instance", "Name"],
    "ins_name_container": ["Instance", "NameContainer"],
    "ins_class_desc": ["Instance", "ClassDescriptor"],
    "ins_class_name": ["Instance", "ClassName"],
    "ins_parent": ["Instance", "Parent"],
    "ins_children_start": ["Instance", "ChildrenStart"],
    "ins_children_end": ["Instance", "ChildrenEnd"],
    "module_bytecode": ["ModuleScript", "ByteCode"],
    "local_bytecode": ["LocalScript", "ByteCode"],
    "bytecode_ptr": ["ByteCode", "Pointer"],
    "bytecode_size": ["ByteCode", "Size"],
    "value": ["Misc", "Value"],
    "string_length": ["Misc", "StringLength"]
}

class Offsets:
    def __init__(self, data):
        self.fakeDatamodelPtr = data["fake_datamodel_ptr"]
        self.realDatamodelPtr = data["real_datamodel_ptr"]
        self.insName = data["ins_name"]
        self.insNameContainer = data["ins_name_container"]
        self.insClassDesc = data["ins_class_desc"]
        self.insClassName = data["ins_class_name"]
        self.insParent = data["ins_parent"]
        self.insChildrenStart = data["ins_children_start"]
        self.insChildrenEnd = data["ins_children_end"]
        self.moduleBytecode = data["module_bytecode"]
        self.bytecodePtr = data["bytecode_ptr"]
        self.bytecodeSize = data["bytecode_size"]
        self.fflagEnableLoadModule = data["fflag_enable_load_module"]
        self.fflagTaskSchedulerTargetFps = data.get("fflag_task_scheduler_target_fps")
        self.value = data["value"]
        self.stringLength = data["string_length"]

class VersionError(Exception): pass
class JSONError(Exception): pass

def silentExit():
    input("Press ENTER to continue . . .")
    exit()

def update(version):
    print(f'Fetching offsets for {version} ...')
    offsets = requests.get(f"https://offsets.imtheo.lol/{version}/offsets.json")
    fflags = requests.get(f"https://offsets.imtheo.lol/{version}/fflags.json")
    try:
        j = offsets.json()
        jf = fflags.json()

        if 'error' in j or 'error' in jf:
            apiError = j.get('error') or jf.get('error')
            raise VersionError(f"offsets.imtheo.lol has no offsets for {version} (API said: {apiError})")

        cache = {
            "schema": 2,
            "roblox_version": version,
            "offsets": {
                "fflag_enable_load_module": jf["FFlagOffsets"]["FFlags"]["EnableLoadModule"]
            }
        }

        fpsCap = jf["FFlagOffsets"]["FFlags"].get("TaskSchedulerTargetFps")
        if fpsCap is not None:
            cache["offsets"]["fflag_task_scheduler_target_fps"] = fpsCap

        for name, path in offsetsToCopy.items():
            value = j["Offsets"]
            for i in path:
                value = value[i]
            cache["offsets"][name] = value

        with open(appData / 'offset_cache.json', 'w') as f:
            f.write(json.dumps(cache, indent=4))
    except requests.JSONDecodeError:
        raise JSONError("Not JSON")

def check(version):
    upd = False
    print('Current Roblox version:', version)

    if os.path.exists(appData / 'offset_cache.json'):
        with open(appData / 'offset_cache.json', 'r') as f:
            j = json.loads(f.read())
            print('Cached Roblox version:', j.get('roblox_version', '(none)'))
            if 'schema' not in j or j['schema'] != 2:
                upd = True
            elif j["roblox_version"] != version:
                upd = True
    else:
        print('No offset cache found')
        upd = True

    if upd:
        print("New version found. Updating!")
        try:
            update(version)
        except VersionError as e:
            print(e)
            print("Your Roblox instance might have updated and offsets aren't supported yet.\n"
                  "You might have to wait for an update from offsets.imtheo.lol.\n"
                  "Please try again later.")
            silentExit()
        except JSONError:
            print("Could not retrieve offsets. The domain used might be down.")
            silentExit()
        except requests.exceptions.ConnectionError:
            print("Could not retrieve offsets. Please check your internet connection.")
            silentExit()
        except Exception as e:
            print("Unknown error. Traceback:")
            traceback.print_exc()
            silentExit()
        print("Updating completed")

def get():
    with open(appData / 'offset_cache.json', 'r') as f:
        d = json.loads(f.read())
    return Offsets(d["offsets"])