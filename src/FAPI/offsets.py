import json
import os.path
import requests
import traceback
from pathlib import Path

appdata = Path(os.environ['APPDATA']+'\\FunnyExecutor')
offsets_to_copy = {
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
        self.fake_datamodel_ptr = data["fake_datamodel_ptr"]
        self.real_datamodel_ptr = data["real_datamodel_ptr"]
        self.ins_name = data["ins_name"]
        self.ins_name_container = data["ins_name_container"]
        self.ins_class_desc = data["ins_class_desc"]
        self.ins_class_name = data["ins_class_name"]
        self.ins_parent = data["ins_parent"]
        self.ins_children_start = data["ins_children_start"]
        self.ins_children_end = data["ins_children_end"]
        self.module_bytecode = data["module_bytecode"]
        self.bytecode_ptr = data["bytecode_ptr"]
        self.bytecode_size = data["bytecode_size"]
        self.fflag_enable_load_module = data["fflag_enable_load_module"]
        self.fflag_task_scheduler_target_fps = data.get("fflag_task_scheduler_target_fps")
        self.value = data["value"]
        self.string_length = data["string_length"]

class VersionError(Exception): pass
class JSONError(Exception): pass

def silent_exit():
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
            api_error = j.get('error') or jf.get('error')
            raise VersionError(f"offsets.imtheo.lol has no offsets for {version} (API said: {api_error})")

        cache = {
            "schema": 2,
            "roblox_version": version,
            "offsets": {
                "fflag_enable_load_module": jf["FFlagOffsets"]["FFlags"]["EnableLoadModule"]
            }
        }

        # optional, not every dump may carry it
        fps_cap = jf["FFlagOffsets"]["FFlags"].get("TaskSchedulerTargetFps")
        if fps_cap is not None:
            cache["offsets"]["fflag_task_scheduler_target_fps"] = fps_cap

        for name, path in offsets_to_copy.items():
            value = j["Offsets"]
            for i in path:
                value = value[i]
            cache["offsets"][name] = value

        with open(appdata / 'offset_cache.json', 'w') as f:
            f.write(json.dumps(cache, indent=4))
    except requests.JSONDecodeError:
        raise JSONError("Not JSON")

def check(version):
    upd = False
    print('Current Roblox version:', version)

    if os.path.exists(appdata / 'offset_cache.json'):
        with open(appdata / 'offset_cache.json', 'r') as f:
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
            silent_exit()
        except JSONError:
            print("Could not retrieve offsets. The domain used might be down.")
            silent_exit()
        except requests.exceptions.ConnectionError:
            print("Could not retrieve offsets. Please check your internet connection.")
            silent_exit()
        except Exception as e:
            print("Unknown error. Traceback:")
            traceback.print_exc()
            silent_exit()
        print("Updating completed")

def get():
    with open(appdata / 'offset_cache.json', 'r') as f:
        d = json.loads(f.read())
    return Offsets(d["offsets"])