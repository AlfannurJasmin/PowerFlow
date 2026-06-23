"""
PowerFlow - Tkinter HMI
Run with: python gui.py  (from inside the app/ folder)
"""

import queue
import tkinter as tk

from simulator import ProductionLine
from influx_client import InfluxWriter

STATE_COLORS = {
    "IDLE": "#9e9e9e",
    "RUNNING": "#2e7d32",
    "STOPPED": "#f9a825",
    "FAULT": "#c62828",
}

INFLUX_PUSH_INTERVAL_MS = 2000


class PowerFlowApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PowerFlow - USB Power Bank Production Line")
        self.root.geometry("780x580")
        self.root.configure(bg="#1e1e1e")

        self._snapshot_queue = queue.Queue()
        self.latest_snapshot = {
            "state": "IDLE", "stage": "Battery Installation",
            "products_produced": 0, "defective_products": 0,
            "fault_reason": None, "log_entries": [],
        }

        self.line = ProductionLine(on_change=self._on_simulator_change)
        self.influx = InfluxWriter()

        self._build_ui()
        self._poll_queue()
        self._push_to_influx_loop()

    def _build_ui(self):
        tk.Label(self.root, text="PowerFlow \u2014 USB Power Bank Production Line",
                 font=("Segoe UI", 16, "bold"), bg="#1e1e1e", fg="white").pack(pady=(15, 5))

        self.state_label = tk.Label(self.root, text="STATE: IDLE", font=("Segoe UI", 14, "bold"),
                                     bg=STATE_COLORS["IDLE"], fg="white", width=30, height=2)
        self.state_label.pack(pady=10)

        info_frame = tk.Frame(self.root, bg="#1e1e1e")
        info_frame.pack(pady=5)

        self.stage_label = self._info_row(info_frame, "Current stage:", "Battery Installation", 0)
        self.produced_label = self._info_row(info_frame, "Products produced:", "0", 1)
        self.defective_label = self._info_row(info_frame, "Defective products:", "0", 2)
        self.fault_label = self._info_row(info_frame, "Fault reason:", "-", 3)
        self.influx_label = self._info_row(info_frame, "InfluxDB status:", "connecting...", 4)

        btn_frame = tk.Frame(self.root, bg="#1e1e1e")
        btn_frame.pack(pady=15)

        self.start_btn = tk.Button(btn_frame, text="START", width=12, height=2, bg="#2e7d32", fg="white",
                                    font=("Segoe UI", 10, "bold"), command=self._on_start)
        self.start_btn.grid(row=0, column=0, padx=8)

        self.stop_btn = tk.Button(btn_frame, text="STOP", width=12, height=2, bg="#f9a825", fg="white",
                                   font=("Segoe UI", 10, "bold"), command=self._on_stop)
        self.stop_btn.grid(row=0, column=1, padx=8)

        self.reset_btn = tk.Button(btn_frame, text="RESET", width=12, height=2, bg="#c62828", fg="white",
                                    font=("Segoe UI", 10, "bold"), command=self._on_reset)
        self.reset_btn.grid(row=0, column=2, padx=8)

        tk.Label(self.root, text="Event log:", bg="#1e1e1e", fg="white", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=20)

        log_frame = tk.Frame(self.root, bg="#1e1e1e")
        log_frame.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        self.log_text = tk.Text(log_frame, height=12, bg="#111111", fg="#00e676", font=("Consolas", 9))
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar = tk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.log_text.config(yscrollcommand=scrollbar.set)
        self.log_text.config(state="disabled")

    def _info_row(self, parent, label_text, value_text, row):
        tk.Label(parent, text=label_text, bg="#1e1e1e", fg="#bbbbbb", font=("Segoe UI", 10), width=18, anchor="w").grid(row=row, column=0, sticky="w", pady=3)
        value_label = tk.Label(parent, text=value_text, bg="#1e1e1e", fg="white", font=("Segoe UI", 10, "bold"), width=30, anchor="w")
        value_label.grid(row=row, column=1, sticky="w", pady=3)
        return value_label

    def _on_start(self):
        self.line.start()

    def _on_stop(self):
        self.line.stop()

    def _on_reset(self):
        self.line.reset()

    def _on_simulator_change(self, snapshot):
        self._snapshot_queue.put(snapshot)

    def _poll_queue(self):
        try:
            while True:
                snapshot = self._snapshot_queue.get_nowait()
                self.latest_snapshot = snapshot
                self._render(snapshot)
        except queue.Empty:
            pass
        self.root.after(150, self._poll_queue)

    def _render(self, snapshot):
        state = snapshot["state"]
        self.state_label.config(text=f"STATE: {state}", bg=STATE_COLORS.get(state, "#444444"))
        self.stage_label.config(text=snapshot["stage"])
        self.produced_label.config(text=str(snapshot["products_produced"]))
        self.defective_label.config(text=str(snapshot["defective_products"]))
        self.fault_label.config(text=snapshot["fault_reason"] or "-")
        self.start_btn.config(state="disabled" if state == "RUNNING" else "normal")
        self.stop_btn.config(state="normal" if state == "RUNNING" else "disabled")
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.insert("end", "\n".join(snapshot["log_entries"]))
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def _push_to_influx_loop(self):
        ok = self.influx.write_snapshot(self.latest_snapshot)
        self.influx_label.config(text="connected" if ok else "disconnected (check Docker)",
                                  fg="#66bb6a" if ok else "#ef5350")
        self.root.after(INFLUX_PUSH_INTERVAL_MS, self._push_to_influx_loop)

    def on_close(self):
        self.influx.close()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = PowerFlowApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()