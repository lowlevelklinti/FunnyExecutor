import time

import win32gui
import win32process
import pymem

from . import offsets

class CustomOffsets:
    moduleBytecode = 0x128
    bytecodeSize = 0x28
    bytecodePtr = 0x18
    localBytecode = 0x180

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

    @property
    def datamodel(self):
        try:
            fakedm = self.mem.read_ulonglong(self.mem.base_address + self.offsets.fakeDatamodelPtr)
            realdm = self.mem.read_ulonglong(fakedm + self.offsets.realDatamodelPtr)
            if not realdm:
                return None
            return Instance(self, realdm)
        except:
            return None

    def fromClassName(self, x):
        x = Instance(self, x)
        name = x.className
        if name in classes:
            return classes[name](self, x.address)
        else:
            return x

    def setFpsCap(self, fps: int):
        offset = self.offsets.fflagTaskSchedulerTargetFps
        addr = self.mem.base_address + offset
        self.mem.write_int(addr, fps)

    def getFpsCap(self) -> int:
        offset = self.offsets.fflagTaskSchedulerTargetFps
        return self.mem.read_int(self.mem.base_address + offset)

class Instance:
    def __init__(self, rbx: Roblox, addr):
        self.memory = rbx.mem
        self.offsets = rbx.offsets
        self.address = addr
        self._roblox = rbx

    @property
    def name(self):
        try:
            if not self.address:
                return None
            container = self.memory.read_ulonglong(self.address + self.offsets.insNameContainer)
            ptr = container + self.offsets.insName
            try: return self.memory.read_string(self.memory.read_ulonglong(ptr))
            except: pass
            try: return self.memory.read_string(ptr)
            except: pass
        except:
            pass
        return None

    @property
    def className(self):
        desc = self.memory.read_ulonglong(self.address + self.offsets.insClassDesc)
        name = self.memory.read_ulonglong(desc + self.offsets.insClassName)

        if name:
            return self.memory.read_string(name)
        return None

    @property
    def parent(self):
        ptr = self.address + self.offsets.insParent
        par = self.memory.read_ulonglong(ptr)
        if par:
            return Instance(self._roblox, par)
        return None

    def getChildren(self):
        base = self.address

        children = self.memory.read_ulonglong(base + self.offsets.insChildrenStart)

        if children == 0:
            return []

        start = self.memory.read_ulonglong(children)
        end = self.memory.read_ulonglong(children + self.offsets.insChildrenEnd)

        size = 16

        if start == 0 or end == 0:
            return None

        if end < start:
            print(f'corrupted child array: {hex(start)} > {hex(end)}')
            return None

        children = []

        for ptr in range(start, end, size):
            try:
                childAddress = self.memory.read_ulonglong(ptr)

                if childAddress == 0:
                    continue

                ins = self._roblox.fromClassName(childAddress)

                children.append(ins)

            except: pass

        return children

    def findFirstChild(self, name, recursive=False):
        children = self.getDescendants() if recursive else self.getChildren()
        for i in children:
            if i and i.name == name:
                return i

        return None

    def waitForChild(self, name, timeout):
        child = None
        finish = time.time()+timeout
        while not child and time.time() < finish:
            child = self.findFirstChild(name)
            time.sleep(0.02)

        return child

    def findFirstChildByClass(self, name, recursive=False):
        children = self.getDescendants() if recursive else self.getChildren()
        for i in children:
            if i and i.className == name:
                return i

        return None

    def getDescendants(self):
        l = []

        def loop(ins):
            for i in ins.getChildren():
                l.append(i)
                if len(i.getChildren()) > 0:
                    loop(i)

        loop(self)
        return l

    def find(self, *path):
        current = self
        for i in path:
            if not current:
                return None
            current = current.findFirstChild(i)
            if not current:
                return None
        return current

    def getFullName(self):
        if self.className == 'DataModel':
            return 'game'

        parent = self
        path = [self.name]
        while parent.className != 'DataModel':
            parent = parent.parent
            path.append('game' if parent.className == 'DataModel' else parent.name)

        return '.'.join(path[::-1])

    def __repr__(self):
        return f'<{self.className} "{self.name}">'

memCommit = 0x00001000
memReserve = 0x00002000
memRelease = 0x00008000
pageReadwrite = 0x04

class Script(Instance):
    def exploit(self, bytecode: bytes):
        ptr = self.memory.read_ulonglong(self.address + CustomOffsets.moduleBytecode)
        bytecodebuf = self.memory.read_ulonglong(ptr + CustomOffsets.bytecodePtr)
        size = self.memory.read_ulonglong(ptr + CustomOffsets.bytecodeSize)

        buffer = pymem.memory.allocate_memory(
            self.memory.process_handle,
            len(bytecode),
            allocation_type=memCommit | memReserve,
            protection_type=pageReadwrite
        )

        self.memory.write_bytes(buffer, bytecode, len(bytecode))

        if self.memory.read_bytes(buffer, len(bytecode)) != bytecode:
            print("writing error")
            return lambda: None

        self.memory.write_ulonglong(ptr + CustomOffsets.bytecodePtr, buffer)
        self.memory.write_ulonglong(ptr + CustomOffsets.bytecodeSize, len(bytecode))

        return lambda: (
            self.memory.write_ulonglong(ptr + CustomOffsets.bytecodePtr, bytecodebuf),
            self.memory.write_ulonglong(ptr + CustomOffsets.bytecodeSize, size),
            pymem.memory.free_memory(self.memory.process_handle, buffer, free_type=memRelease)
        )

    def getAuthenticBytecode(self):  # roblox KEEPS changing the damn offsets omg bro
        offset = CustomOffsets.moduleBytecode
        if self.className == 'LocalScript':
            offset = CustomOffsets.localBytecode

        ptr = self.memory.read_ulonglong(self.address + offset)
        buffer = self.memory.read_ulonglong(ptr + CustomOffsets.bytecodePtr)
        size = self.memory.read_ulonglong(ptr + CustomOffsets.bytecodeSize)

        if buffer == 0 or size == 0:
            return b''

        return self.memory.read_bytes(buffer, size)

    def setIsCoreScript(self, val):
        self.memory.write_bool(self.address+0, val)

class StringValue(Instance):
    def __init__(self, rbx: Roblox, addr):
        super().__init__(rbx, addr)

        self.contentPtr = self.memory.read_ulonglong(addr+self.offsets.value)
        self.sizePtr = addr+self.offsets.value+self.offsets.stringLength
        self._isBuffer = False

    def setValue(self, content: str):
        if self._isBuffer:
            pymem.memory.free_memory(self.memory.process_handle, self.contentPtr, free_type=memRelease)

        self.contentPtr = pymem.memory.allocate_memory(
            self.memory.process_handle,
            len(content),
            allocation_type=memCommit | memReserve,
            protection_type=pageReadwrite
        )
        self.memory.write_string(self.contentPtr, content)
        self.memory.write_ulonglong(self.address+self.offsets.value, self.contentPtr)
        self.memory.write_int(self.sizePtr, len(content))
        self._isBuffer = True

    def getValue(self):
        return self.memory.read_string(self.contentPtr, self.memory.read_int(self.sizePtr))

class BoolValue(Instance):
    def setValue(self, val: bool):
        self.memory.write_bool(self.address+self.offsets.value, val)

    def getValue(self):
        return self.memory.read_bool(self.address+self.offsets.value)

class ObjectValue(Instance):
    @property
    def value(self):
        ptr = self.memory.read_ulonglong(self.address + self.offsets.value)
        if not ptr:
            return None
        return self._roblox.fromClassName(ptr)

classes = {
    'Instance': Instance,
    "ModuleScript": Script,
    "LocalScript": Script,
    "StringValue": StringValue,
    "BoolValue": BoolValue,
    "ObjectValue": ObjectValue
}

def getHwnd(processHandle):
    targetPid = win32process.GetProcessId(processHandle)
    matchingHwnds = []

    def enumWindowsCallback(hwnd, _):
        _, windowPid = win32process.GetWindowThreadProcessId(hwnd)

        if windowPid == targetPid:
            if win32gui.IsWindowVisible(hwnd):
                matchingHwnds.append(hwnd)
        return True

    win32gui.EnumWindows(enumWindowsCallback, None)

    return matchingHwnds