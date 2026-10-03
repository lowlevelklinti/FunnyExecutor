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
    # Roblox keeps building CoreGui (RobloxGui.Topbar, PlayerList, InspectAndBuy, ...)
    # for the first seconds of a DataModel. Hijacking PlayerListManager while that
    # is still happening makes RobloxGui's own modules load with a nil module value
    # ("attempt to index nil with 'Event'" in TopBar/GamepadConnector), the top bar
    # never gets built and F9 fills up with errors. So never touch anything until
    # the client UI is actually up and the DataModel has settled.
    MIN_DM_AGE = 3.0
    READY_TIMEOUT = 30.0

    def __init__(self, rbx: sdk.Roblox = None):
        if not robloxOpen():
            raise ExecutionError('Roblox is not open')

        self.sdk: sdk.Roblox = rbx if rbx else getSdk()
        bridge.setSdk(self.sdk)
        self.strval = None
        self._injecting = False
        self._handledDms = set()
        self._updAddr = None
        self._dmAddr = None
        self._dmSince = 0.0

    def _liveDataModel(self):
        """Current DataModel, with per-place state reset whenever it changes.

        DataModel addresses are recycled by Roblox after a rejoin/teleport, so
        everything keyed by address has to be dropped when the address changes.
        """
        dm = self.sdk.datamodel
        if not dm or dm.name != 'Ugc' or not dm.address:
            return None

        if dm.address != self._dmAddr:
            self._dmAddr = dm.address
            self._dmSince = time.time()
            self._updAddr = None
            self._handledDms.discard(dm.address)
            bridge.forgetDm(dm.address)

        return dm

    def clientReady(self, dm=None) -> bool:
        """True once Roblox finished booting its own UI, safe to inject."""
        try:
            if dm is None:
                dm = self._liveDataModel()
            if not dm:
                return False

            age = time.time() - self._dmSince
            if age < self.MIN_DM_AGE:
                return False

            # don't stay stuck forever on a place that never parents a PlayerGui
            if age >= self.READY_TIMEOUT:
                return True

            players = dm.findFirstChild('Players')
            if not players:
                return False

            # the local player's PlayerGui only gets parented to CoreGui once the
            # client UI is up, which is a late enough signal for us
            for player in (players.getChildren() or []):
                gui = player.findFirstChild('PlayerGui')
                if gui is not None and gui.parent is not None:
                    return True

            return False
        except:
            return False

    @property
    def injected(self):
        try:
            dm = self._liveDataModel()
            if not dm:
                return False
            if not psutil.pid_exists(self.sdk.mem.process_id):
                return False
            if dm.find('CoreGui', '_funnyexecutor') is not None:
                return True
            return bridge.isDmConfirmed(dm.address)
        except:
            return False

    def inject(self):
        if self._injecting:
            return
        if self.injected:
            print("Skipping injection, root folder already exists.")
            return

        dm = self._liveDataModel()
        if not dm:
            return

        if dm.address in self._handledDms:
            return

        if not self.clientReady(dm):
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
            game = self._liveDataModel()
            if not game or game.address != dm.address:
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

            stateAddr = plm.address + sdk.CustomOffsets.moduleState
            prevState = rbx.mem.read_int(stateAddr)
            rbx.mem.write_int(stateAddr, 0)

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
            triggered = bridge.initReceivedEvent.wait(timeout=2.0)
            time.sleep(0.25)
            revert()

            # the injected script became the cached return value of this module,
            # put the state back so Roblox is never left with a half-required module
            rbx.mem.write_int(stateAddr, prevState)

            # only close the menu again when our keypress actually opened it,
            # otherwise we'd leave the menu open instead
            if triggered:
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
        game = self._liveDataModel()
        if not game:
            raise ExecutionError("Lost the current place, try injecting again")
        updAddr = self._updAddr

        if updAddr is None or updAddr[0] != game.address:
            coreGui: sdk.Instance = game.findFirstChild('CoreGui')
            root: sdk.Instance = coreGui.findFirstChild('_funnyexecutor') if coreGui else None
            if root is None:
                raise ExecutionError("Injection is gone, try injecting again")
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
