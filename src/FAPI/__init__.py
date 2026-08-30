import base64

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

class ExecutionError(Exception): pass

class Executor:
    def __init__(self, rbx: sdk.Roblox = None):
        if not roblox_open():
            raise ExecutionError('Roblox is not open')

        self.sdk: sdk.Roblox = rbx if rbx else get_sdk()
        self.strval = None

    @property
    def injected(self):
        try:
            if self.sdk.datamodel.name != "Ugc":
                return False
        except:
            return False

        if not psutil.pid_exists(self.sdk.mem.process_id):
            return False

        return self.sdk.datamodel.find('CoreGui', '_funnyexecutor') is not None

    def inject(self):
        if self.injected:
            print("Skipping injection, root folder already exists.")
            return

        print('--- INJECTING ---')
        if not psutil.pid_exists(self.sdk.mem.process_id):
            self.sdk = get_sdk()

        rbx = self.sdk
        game = rbx.datamodel

        hwnd = sdk.get_hwnd(rbx.mem.process_handle)[0]

        print("Client HWND:", hex(hwnd), '\n')

        plm = game.find('CoreGui', 'RobloxGui', 'Modules', 'PlayerList', 'PlayerListManager')

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

        oldfg = win32gui.GetForegroundWindow()
        win32gui.SetForegroundWindow(hwnd)
        pydirectinput.press('esc')

        print('sent escape key (triggered plm)', '\n')
        revert()

        pydirectinput.press('esc')
        win32gui.SetForegroundWindow(oldfg)

        print('reverted bytecode replacement', '\n')

        print('Injected')

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

        bridge.set_source(base64.b64encode(Luau.compile(source)))
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
    ph = pymem.Pymem('RobloxPlayerBeta.exe').process_handle
    if ph:
        if sdk.get_hwnd(ph):
            return True
        else:
            return False
    return False
