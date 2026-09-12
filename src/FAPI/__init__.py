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
luau_modules = parent / 'luau'
bridge.start_bridge()

def force_foreground(hwnd):
    try:
        fore_hwnd = win32gui.GetForegroundWindow()
        if fore_hwnd == hwnd:
            return True
        fore_thread, _ = win32process.GetWindowThreadProcessId(fore_hwnd)
        curr_thread = win32process.GetCurrentThreadId()
        if fore_thread != curr_thread:
            ctypes.windll.user32.AttachThreadInput(curr_thread, fore_thread, True)
            ctypes.windll.user32.BringWindowToTop(hwnd)
            ctypes.windll.user32.ShowWindow(hwnd, 5)
            ctypes.windll.user32.SetForegroundWindow(hwnd)
            ctypes.windll.user32.AttachThreadInput(curr_thread, fore_thread, False)
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
        if not roblox_open():
            raise ExecutionError('Roblox is not open')

        self.sdk: sdk.Roblox = rbx if rbx else get_sdk()
        bridge.set_sdk(self.sdk)
        self.strval = None
        self._injecting = False
        self._handled_dms = set()

    @property
    def injected(self):
        try:
            dm = self.sdk.datamodel
            if not dm or dm.name != "Ugc":
                return False
            if not psutil.pid_exists(self.sdk.mem.process_id):
                return False
            if bridge.is_dm_confirmed(dm.address):
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

        if dm.address in self._handled_dms:
            return

        players = dm.find_first_child('Players')
        if not players or not players.get_children():
            return

        self._injecting = True
        try:
            print('Injecting')
            if not psutil.pid_exists(self.sdk.mem.process_id):
                self.sdk = get_sdk()
                bridge.set_sdk(self.sdk)

            rbx = self.sdk
            game = rbx.datamodel
            if not game:
                return

            hwnds = sdk.get_hwnd(rbx.mem.process_handle)
            if not hwnds:
                return
            hwnd = hwnds[0]

            print("Client HWND:", hex(hwnd), '\n')

            plm = game.find('CoreGui', 'RobloxGui', 'Modules', 'PlayerList', 'PlayerListManager')
            if not plm:
                return

            print('got PlayerListManager:', hex(plm.address))

            EnableLoadModule = rbx.offsets.fflag_enable_load_module
            addr = rbx.mem.base_address + EnableLoadModule

            print('got EnableLoadModule:', hex(addr))

            rbx.mem.write_bool(addr, True)
            rbx.mem.write_int(plm.address + 0x170, 0)

            print('set PlayerListManager.ModuleState to 0')

            with open(luau_modules / 'init.bin', 'rb') as f:
                bytecode = f.read()
            print(bytecode)

            revert = plm.exploit(bytecode)

            print('replace bytecode in Jest', '\n')

            bridge.init_received_event.clear()

            oldfg = win32gui.GetForegroundWindow()
            force_foreground(hwnd)
            time.sleep(0.05)

            pydirectinput.press('esc')
            bridge.init_received_event.wait(timeout=0.6)
            time.sleep(0.05)
            revert()
            pydirectinput.press('esc')
            if oldfg and oldfg != hwnd:
                force_foreground(oldfg)

            print('reverted bytecode replacement', '\n')

            finish = time.time() + 2.0
            while time.time() < finish:
                if self.injected:
                    break
                time.sleep(0.02)

            if self.injected:
                self._handled_dms.add(dm.address)
                print('Injected')
        finally:
            self._injecting = False

    def execute(self, source: str | bytes):
        if not self.injected:
            raise ExecutionError("You must inject before executing. Tip: add FAPI.inject() before execution")

        rbx = self.sdk
        game = rbx.datamodel

        coregui: sdk.Instance = game.find_first_child('CoreGui')
        root: sdk.Instance = coregui.find_first_child('_funnyexecutor')

        if root is None:
            raise ExecutionError("Failed to get instances neccessary for execution (has injection failed?)")

        upd: sdk.BoolValue = root.find_first_child('UpdateIndicator')

        bridge.set_source(Luau.compile(source))
        upd.set_value(not upd.get_value())

        print("Executed")

def get_sdk():
    return sdk.Roblox()

def check_process_by_name(process_name):
    for proc in psutil.process_iter(['name']):
        try:
            if proc.name().lower() == process_name.lower():
                return proc.pid
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False

def process_has_window(target_pid):
    has_window = False

    def enum_callback(hwnd, extra):
        nonlocal has_window
        if win32gui.IsWindowVisible(hwnd):
            _, win_pid = win32process.GetWindowThreadProcessId(hwnd)
            if win_pid == target_pid:
                has_window = True
                return False
        return True
    win32gui.EnumWindows(enum_callback, None)
    return has_window

def roblox_open():
    try:
        if not check_process_by_name('RobloxPlayerBeta.exe'):
            return False
        ph = pymem.Pymem('RobloxPlayerBeta.exe').process_handle
        if ph:
            if sdk.get_hwnd(ph):
                return True
            else:
                return False
        return False
    except:
        return False
