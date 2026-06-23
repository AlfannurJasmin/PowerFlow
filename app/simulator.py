"""
PowerFlow - Production Line Simulator
Core finite-state-machine logic for the USB Power Bank assembly line.
"""

import random
import threading
import time
from datetime import datetime
from enum import Enum


class LineState(Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    FAULT = "FAULT"


class FaultType(Enum):
    BATTERY_MISSING = "Battery Missing"
    PCB_DEFECT = "PCB Defect"
    ASSEMBLY_ERROR = "Assembly Error"
    QUALITY_TEST_FAILED = "Quality Test Failed"


STAGES = [
    "Battery Installation",
    "PCB Installation",
    "Case Assembly",
    "Quality Testing",
    "Finished Product",
]

STAGE_FAULT_MAP = {
    "Battery Installation": FaultType.BATTERY_MISSING,
    "PCB Installation": FaultType.PCB_DEFECT,
    "Case Assembly": FaultType.ASSEMBLY_ERROR,
    "Quality Testing": FaultType.QUALITY_TEST_FAILED,
}

FAULT_PROBABILITY = 0.08
STAGE_DURATION_SECONDS = 2.0


class ProductionLine:
    def __init__(self, on_change=None):
        self._lock = threading.Lock()
        self.state = LineState.IDLE
        self.stage_index = 0
        self.products_produced = 0
        self.defective_products = 0
        self.fault_reason = None
        self.log_entries = []
        self._on_change = on_change
        self._thread = None
        self._running_flag = threading.Event()
        self._log(f"Line initialized. Ready at stage '{self._current_stage_name()}'")

    def start(self):
        with self._lock:
            if self.state in (LineState.IDLE, LineState.STOPPED):
                self.state = LineState.RUNNING
                self.fault_reason = None
                self._log(f"Line STARTED at stage '{self._current_stage_name()}'")
                self._running_flag.set()
                if self._thread is None or not self._thread.is_alive():
                    self._thread = threading.Thread(target=self._run_loop, daemon=True)
                    self._thread.start()
                self._notify()

    def stop(self):
        with self._lock:
            if self.state == LineState.RUNNING:
                self.state = LineState.STOPPED
                self._running_flag.clear()
                self._log("Line STOPPED by operator")
                self._notify()

    def reset(self):
        with self._lock:
            self.state = LineState.IDLE
            self.stage_index = 0
            self.fault_reason = None
            self._running_flag.clear()
            self._log("Line RESET to IDLE, stage pointer cleared")
            self._notify()

    def _run_loop(self):
        while True:
            if not self._running_flag.wait(timeout=0.2):
                continue
            with self._lock:
                if self.state != LineState.RUNNING:
                    continue
            time.sleep(STAGE_DURATION_SECONDS)
            with self._lock:
                if self.state != LineState.RUNNING:
                    continue
                self._process_stage()
                self._notify()

    def _process_stage(self):
        stage_name = self._current_stage_name()
        if stage_name in STAGE_FAULT_MAP and random.random() < FAULT_PROBABILITY:
            fault = STAGE_FAULT_MAP[stage_name]
            self.state = LineState.FAULT
            self.fault_reason = fault.value
            self.defective_products += 1
            self._running_flag.clear()
            self._log(f"FAULT at '{stage_name}': {fault.value} -- product marked defective")
            return
        self.stage_index += 1
        if self.stage_index >= len(STAGES):
            self.products_produced += 1
            self._log(f"Product #{self.products_produced} completed successfully")
            self.stage_index = 0
        else:
            self._log(f"Advanced to stage '{self._current_stage_name()}'")

    def _current_stage_name(self):
        return STAGES[self.stage_index]

    def _log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_entries.append(f"[{timestamp}] {message}")
        if len(self.log_entries) > 200:
            self.log_entries.pop(0)

    def _notify(self):
        if self._on_change:
            self._on_change(self.snapshot())

    def snapshot(self):
        return {
            "state": self.state.value,
            "stage": self._current_stage_name(),
            "products_produced": self.products_produced,
            "defective_products": self.defective_products,
            "fault_reason": self.fault_reason,
            "log_entries": list(self.log_entries[-50:]),
        }


if __name__ == "__main__":
    def printer(snap):
        print(snap)

    line = ProductionLine(on_change=printer)
    line.start()
    time.sleep(12)
    line.stop()
    print("Final snapshot:", line.snapshot())