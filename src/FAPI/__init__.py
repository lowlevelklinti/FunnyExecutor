import time
import ctypes
import pymem

from . import sdk, bridge
from .compiler import Luau

from pathlib import Path

import win32gui
import win32process
import pydirectinput
import psutil

parent = Path(__file__).resolve().parent
luauModules = parent / 'luau'
bridge.startBridge()

def forceForeground(hwnd):
    try:
        foregroundHwnd = win32gui.GetForegroundWindow()
        if foregroundHwnd == hwnd:
            return True
        foregroundThread, _ = win32process.GetWindowThreadProcessId(foregroundHwnd)
        currentThread = win32process.GetCurrentThreadId()
        if foregroundThread != currentThread:
            ctypes.windll.user32.AttachThreadInput(currentThread, foregroundThread, True)
            ctypes.windll.user32.BringWindowToTop(hwnd)
            ctypes.windll.user32.ShowWindow(hwnd, 5)
            ctypes.windll.user32.SetForegroundWindow(hwnd)
            ctypes.windll.user32.AttachThreadInput(currentThread, foregroundThread, False)
        else:
            ctypes.windll.user32.BringWindowToTop(hwnd)
            ctypes.windll.user32.ShowWindow(hwnd, 5)
            ctypes.windll.user32.SetForegroundWindow(hwnd)
        return True
    except:
        try:
            win32gui.SetForegroundWindow(hwnd)
        except:
            pass
        return False

class ExecutionError(Exception): pass

class Executor:
    def __init__(self, rbx: sdk.Roblox = None):
        if not robloxOpen():
            raise ExecutionError('Roblox is not open')

        self.sdk: sdk.Roblox = rbx if rbx else getSdk()
        bridge.setSdk(self.sdk)
        self.strval = None
        self._injecting = False
        self._handledDms = set()
        self._updAddr = None

    @property
    def injected(self):
        try:
            dm = self.sdk.datamodel
            if not dm or dm.name != "Ugc":
                return False
            if not psutil.pid_exists(self.sdk.mem.process_id):
                return False
            if bridge.isDmConfirmed(dm.address):
                return True
            return dm.find('CoreGui', '_funnyexecutor') is not None
        except:
            return False

    def inject(self):
        if self._injecting:
            return
        if self.injected:
            print("Skipping injection, root folder already exists.")
            return

        dm = self.sdk.datamodel
        if not dm or dm.name != "Ugc" or not dm.address:
            return

        if dm.address in self._handledDms:
            return

        players = dm.findFirstChild('Players')
        if not players or not players.getChildren():
            return

        self._injecting = True
        self._updAddr = None
        try:
            print('Injecting')
            if not psutil.pid_exists(self.sdk.mem.process_id):
                self.sdk = getSdk()
                bridge.setSdk(self.sdk)

            rbx = self.sdk
            game = rbx.datamodel
            if not game:
                return

            windowHandles = sdk.getHwnd(rbx.mem.process_handle)
            if not windowHandles:
                return
            hwnd = windowHandles[0]

            print("Client HWND:", hex(hwnd), '\n')

            plm = game.find('CoreGui', 'RobloxGui', 'Modules', 'PlayerList', 'PlayerListManager')
            if not plm:
                return

            print('got PlayerListManager:', hex(plm.address))

            enableLoadModule = rbx.offsets.fflagEnableLoadModule
            addr = rbx.mem.base_address + enableLoadModule

            print('got EnableLoadModule:', hex(addr))

            rbx.mem.write_bool(addr, True)
            rbx.mem.write_int(plm.address + 0x160, 0) ## offset by theholytorch, thanks!

            print('set PlayerListManager.ModuleState to 0')

            with open(luauModules / 'init.bin', 'rb') as f:
                bytecode = f.read()

            revert = plm.exploit(bytecode)

            print('replace bytecode in Jest', '\n')

            bridge.initReceivedEvent.clear()

            oldForegroundHwnd = win32gui.GetForegroundWindow()
            forceForeground(hwnd)
            time.sleep(0.05)

            pydirectinput.press('esc')
            bridge.initReceivedEvent.wait(timeout=0.6)
            time.sleep(0.05)
            revert()
            pydirectinput.press('esc')
            if oldForegroundHwnd and oldForegroundHwnd != hwnd:
                forceForeground(oldForegroundHwnd)

            print('reverted bytecode replacement', '\n')

            finish = time.time() + 2.0
            while time.time() < finish:
                if self.injected:
                    break
                time.sleep(0.02)

            if self.injected:
                self._handledDms.add(dm.address)
                print('Injected')
        finally:
            self._injecting = False

    def execute(self, source: str | bytes):
        if not self.injected:
            raise ExecutionError("You must inject before executing. Tip: add FAPI.inject() before execution")

        rbx = self.sdk
        game = rbx.datamodel
        updAddr = self._updAddr

        if updAddr is None or updAddr[0] != game.address:
            coreGui: sdk.Instance = game.findFirstChild('CoreGui')
            root: sdk.Instance = coreGui.findFirstChild('_funnyexecutor') if coreGui else None
            updateIndicator: sdk.BoolValue = root.findFirstChild('UpdateIndicator')
            updAddr = (game.address, updateIndicator.address)
            self._updAddr = updAddr

        bridge.setSource(Luau.compile(source))

        valueAddr = updAddr[1] + rbx.offsets.value
        rbx.mem.write_bool(valueAddr, not rbx.mem.read_bool(valueAddr))

        print("Executed")

def getSdk():
    return sdk.Roblox()

def checkProcessByName(processName):
    for proc in psutil.process_iter(['name']):
        try:
            if proc.name().lower() == processName.lower():
                return proc.pid
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False

def processHasWindow(targetPid):
    hasWindow = False

    def enumCallback(hwnd, extra):
        nonlocal hasWindow
        if win32gui.IsWindowVisible(hwnd):
            _, windowPid = win32process.GetWindowThreadProcessId(hwnd)
            if windowPid == targetPid:
                hasWindow = True
                return False
        return True
    win32gui.EnumWindows(enumCallback, None)
    return hasWindow

def robloxOpen():
    try:
        if not checkProcessByName('RobloxPlayerBeta.exe'):
            return False
        ph = pymem.Pymem('RobloxPlayerBeta.exe').process_handle
        if ph:
            if sdk.getHwnd(ph):
                return True
            else:
                return False
        return False
    except:
        return False
