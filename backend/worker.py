import time
import threading

import psutil

import FAPI


class RobloxWorker:
    """Manages the FAPI executor lifecycle.

    A daemon thread polls Roblox so a queued injection is retried until the
    game is ready. Inject/execute requests return ``(ok, message)`` tuples
    so the caller (pytauri command) can report back to the UI.
    """

    def __init__(self):
        self.executor = None
        self.sdk = None
        self.injected = False
        self.queued = False
        self._injecting = False
        self._lastInjectTry = 0.0
        self._stop_event = threading.Event()
        self._thread = None

    # lifecycle ---------------------------------------------------------

    def start(self):
        if self._thread is None or not self._thread.is_alive():
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run, daemon=True, name='RobloxWorker')
            self._thread.start()

    def stop(self):
        self._stop_event.set()

    def _run(self):
        while not self._stop_event.wait(0.25):
            self.poll()

    # executor management -------------------------------------------------

    def ensureExecutor(self):
        if self.executor is not None and self.sdk is not None:
            try:
                if psutil.pid_exists(self.sdk.mem.process_id):
                    return True
            except Exception:
                pass
            self.executor = None
            self.sdk = None

        try:
            if not FAPI.robloxOpen():
                self.executor = None
                self.sdk = None
                return False
        except Exception:
            self.executor = None
            self.sdk = None
            return False

        try:
            self.executor = FAPI.Executor()
            self.sdk = self.executor.sdk
            return True
        except Exception:
            self.executor = None
            self.sdk = None
            return False

    def poll(self):
        if self._injecting:
            return

        if not self.ensureExecutor():
            self.queued = False
            self.injected = False
            return

        try:
            self.injected = self.executor.injected
        except Exception:
            self.injected = False

        if not self.injected and self.queued:
            self.tryInject()

    def tryInject(self):
        if self._injecting or self.injected:
            return

        try:
            if self.executor.injected:
                return
            dm = self.sdk.datamodel
            if not dm or dm.name != 'Ugc' or not dm.address:
                return
            if dm.address in self.executor._handledDms:
                return
            players = dm.findFirstChild('Players')
            if not players or not players.getChildren():
                return
        except Exception:
            return

        if time.time() - self._lastInjectTry < 1.0:
            return

        self._lastInjectTry = time.time()
        self._injecting = True
        try:
            self.executor.inject()
        except Exception as e:
            print(e)
        finally:
            self._injecting = False

    # requests from the UI ------------------------------------------------

    def requestInject(self) -> tuple[bool, str | None]:
        if not self.ensureExecutor():
            return False, 'You must have Roblox open to inject'

        try:
            if self.executor.injected:
                return False, 'Already injected'
        except Exception:
            pass

        self.queued = True
        self.tryInject()
        return True, None

    def requestExecute(self, script) -> tuple[bool, str | None]:
        ready = False
        if self.executor is not None:
            try:
                ready = self.executor.injected
            except Exception:
                ready = False

        if not ready:
            return False, 'You must inject before executing'

        try:
            self.executor.execute(script)
            return True, None
        except Exception as e:
            return False, str(e) or 'Execution failed'
