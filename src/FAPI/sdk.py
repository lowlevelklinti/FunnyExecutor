import time

import win32gui
import win32process
import pymem

from . import offsets

class CustomOffsets:
    module_bytecode = 0x138
    module_state = 0x170  # not sure
    bytecode_size = 0x28
    bytecode_ptr = 0x18
    local_bytecode = 0x190

class SdkError(Exception): pass

class Roblox:
    def __init__(self):
        pm = pymem.Pymem('RobloxPlayerBeta.exe')
        self.mem = pm
        self.version = None
        self.offsets = None

        for i in self.mem.list_modules():
            if i.name == 'RobloxPlayerBeta.exe':
                self.version = i.filename.split('\\')[-2]
                break

        if not self.version:
            raise SdkError("Cannot find version")

        print('Roblox version:', self.version)
        offsets.check(self.version)
        self.offsets = offsets.get()

        fakedm = self.mem.read_ulonglong(self.mem.base_address + self.offsets.fake_datamodel_ptr)
        realdm = self.mem.read_ulonglong(fakedm + self.offsets.real_datamodel_ptr)
        self.datamodel = Instance(self, realdm)

    def from_class_name(self, x):
        x = Instance(self, x)
        name = x.class_name
        if name in classes:
            return classes[name](self, x.address)
        else:
            return x

    def set_fps_cap(self, fps: int):
        offset = self.offsets.fflag_task_scheduler_target_fps
        if not offset:
            raise SdkError('FPS cap fflag offset unavailable for this version')
        addr = self.mem.base_address + offset
        self.mem.write_int(addr, fps)

    def get_fps_cap(self) -> int:
        offset = self.offsets.fflag_task_scheduler_target_fps
        if not offset:
            raise SdkError('FPS cap fflag offset unavailable for this version')
        return self.mem.read_int(self.mem.base_address + offset)

class Instance:
    def __init__(self, rbx: Roblox, addr):
        self.memory = rbx.mem
        self.offsets = rbx.offsets
        self.address = addr
        self._rbx = rbx

    @property
    def name(self):  # roblox changed how names work. now theyre in name containers
        container = self.memory.read_ulonglong(self.address + self.offsets.ins_name_container)
        ptr = container + self.offsets.ins_name

        # first check if the container value is another pointer to prevent corrupted strings
        try: return self.memory.read_string(self.memory.read_ulonglong(ptr))
        except: pass

        # if not, dont wrap it in a read_ulonglong
        try: return self.memory.read_string(ptr)
        except: pass

        return None

    @property
    def class_name(self):
        desc = self.memory.read_ulonglong(self.address + self.offsets.ins_class_desc)
        name = self.memory.read_ulonglong(desc + self.offsets.ins_class_name)

        if name:
            return self.memory.read_string(name)
        return None

    @property
    def parent(self):
        ptr = self.address + self.offsets.ins_parent
        par = self.memory.read_ulonglong(ptr)
        if par:
            return Instance(self._rbx, par)
        return None

    def get_children(self):
        base = self.address

        children = self.memory.read_ulonglong(base + self.offsets.ins_children_start)

        if children == 0:
            return []

        start = self.memory.read_ulonglong(children)
        end = self.memory.read_ulonglong(children + self.offsets.ins_children_end)

        size = 16

        if start == 0 or end == 0:
            return None

        if end < start:
            print(f'corrupted child array: {hex(start)} > {hex(end)}')
            return None

        children = []

        for ptr in range(start, end, size):
            try:
                child_addr = self.memory.read_ulonglong(ptr)

                if child_addr == 0:
                    continue

                ins = self._rbx.from_class_name(child_addr)

                children.append(ins)

            except: pass

        return children

    def find_first_child(self, name, recursive=False):
        children = self.get_descendants() if recursive else self.get_children()
        for i in children:
            if i and i.name == name:
                return i

        return None

    def wait_for_child(self, name, timeout):
        child = None
        finish = time.time()+timeout
        while not child and time.time() < finish:
            child = self.find_first_child(name)
            time.sleep(0.02)

        return child

    def find_first_child_by_class(self, name, recursive=False):
        children = self.get_descendants() if recursive else self.get_children()
        for i in children:
            if i and i.class_name == name:
                return i

        return None

    def get_descendants(self):
        l = []

        def loop(ins):
            for i in ins.get_children():
                l.append(i)
                if len(i.get_children()) > 0:
                    loop(i)

        loop(self)
        return l

    def find(self, *path):  # alternative to Instance.Child1.Child2...
        current = self
        for i in path:
            current = current.find_first_child(i)
            if not current:
                return None
        return current

    def get_full_name(self):
        if self.class_name == 'DataModel':
            return 'game'

        parent = self
        path = [self.name]
        while parent.class_name != 'DataModel':
            parent = parent.parent
            path.append('game' if parent.class_name == 'DataModel' else parent.name)

        return '.'.join(path[::-1])

    def __repr__(self):
        return f'<{self.class_name} "{self.name}">'

MEM_COMMIT = 0x00001000
MEM_RESERVE = 0x00002000
MEM_RELEASE = 0x00008000
PAGE_READWRITE = 0x04

class Script(Instance):
    def exploit(self, bytecode: bytes):
        ptr = self.memory.read_ulonglong(self.address + CustomOffsets.module_bytecode)
        bytecodebuf = self.memory.read_ulonglong(ptr + CustomOffsets.bytecode_ptr)
        size = self.memory.read_ulonglong(ptr + CustomOffsets.bytecode_size)

        buffer = pymem.memory.allocate_memory(
            self.memory.process_handle,
            len(bytecode),
            allocation_type=MEM_COMMIT | MEM_RESERVE,
            protection_type=PAGE_READWRITE
        )

        self.memory.write_bytes(buffer, bytecode, len(bytecode))

        if self.memory.read_bytes(buffer, len(bytecode)) != bytecode:
            print("writing error")
            return lambda: None

        self.memory.write_ulonglong(ptr + CustomOffsets.bytecode_ptr, buffer)
        self.memory.write_ulonglong(ptr + CustomOffsets.bytecode_size, len(bytecode))

        return lambda: (
            self.memory.write_ulonglong(ptr + CustomOffsets.bytecode_ptr, bytecodebuf),
            self.memory.write_ulonglong(ptr + CustomOffsets.bytecode_size, size),
            pymem.memory.free_memory(self.memory.process_handle, buffer, free_type=MEM_RELEASE)
        )

    def get_authentic_bytecode(self):  # roblox KEEPS changing the damn offsets omg bro
        offset = CustomOffsets.module_bytecode
        if self.class_name == 'LocalScript':
            offset = CustomOffsets.local_bytecode

        ptr = self.memory.read_ulonglong(self.address + offset)
        buffer = self.memory.read_ulonglong(ptr + CustomOffsets.bytecode_ptr)
        size = self.memory.read_ulonglong(ptr + CustomOffsets.bytecode_size)

        return self.memory.read_bytes(buffer, size)

    def set_iscorescript(self, val):
        self.memory.write_bool(self.address+0, val)

class StringValue(Instance):
    def __init__(self, rbx: Roblox, addr):
        super().__init__(rbx, addr)

        self.content_ptr = self.memory.read_ulonglong(addr+self.offsets.value)
        self.size_ptr = addr+self.offsets.value+self.offsets.string_length
        self._is_buffer = False

    def set_value(self, content: str):
        if self._is_buffer:
            pymem.memory.free_memory(self.memory.process_handle, self.content_ptr, free_type=MEM_RELEASE)

        self.content_ptr = pymem.memory.allocate_memory(
            self.memory.process_handle,
            len(content),
            allocation_type=MEM_COMMIT | MEM_RESERVE,
            protection_type=PAGE_READWRITE
        )
        self.memory.write_string(self.content_ptr, content)
        self.memory.write_ulonglong(self.address+self.offsets.value, self.content_ptr)
        self.memory.write_int(self.size_ptr, len(content))
        self._is_buffer = True

    def get_value(self):
        return self.memory.read_string(self.content_ptr, self.memory.read_int(self.size_ptr))

class BoolValue(Instance):
    def set_value(self, val: bool):
        self.memory.write_bool(self.address+self.offsets.value, val)

    def get_value(self):
        return self.memory.read_bool(self.address+self.offsets.value)

class ObjectValue(Instance):
    @property
    def value(self):
        ptr = self.memory.read_ulonglong(self.address + self.offsets.value)
        if not ptr:
            return None
        return self._rbx.from_class_name(ptr)

classes = {
    'Instance': Instance,
    "ModuleScript": Script,
    "LocalScript": Script,
    "StringValue": StringValue,
    "BoolValue": BoolValue,
    "ObjectValue": ObjectValue
}

def get_hwnd(proc_handle):
    target_pid = win32process.GetProcessId(proc_handle)
    matching_hwnds = []

    def enum_windows_callback(hwnd, _):
        _, window_pid = win32process.GetWindowThreadProcessId(hwnd)

        if window_pid == target_pid:
            if win32gui.IsWindowVisible(hwnd):
                matching_hwnds.append(hwnd)
        return True

    win32gui.EnumWindows(enum_windows_callback, None)

    return matching_hwnds