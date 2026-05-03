from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
from queue import Empty, Queue
import threading
import tkinter as tk
from tkinter import simpledialog

from pynput import keyboard


@dataclass(frozen=True)
class PanelState:
    status: str
    current_asset: str
    next_signal: str
    trades_executed: int
    integrity_status: str
    pin_status: str


class FloatingStopPanel:
    def __init__(self, on_start: Callable[[str, str | None], None], on_stop: Callable[[str], None], logger: logging.Logger) -> None:
        self.on_start = on_start
        self.on_stop = on_stop
        self.logger = logger
        self._queue: Queue[tuple[str, object]] = Queue()
        self._thread: threading.Thread | None = None
        self._root: tk.Tk | None = None
        self._status_var: tk.StringVar | None = None
        self._asset_var: tk.StringVar | None = None
        self._signal_var: tk.StringVar | None = None
        self._trades_var: tk.StringVar | None = None
        self._integrity_var: tk.StringVar | None = None
        self._pin_var: tk.StringVar | None = None
        self._hotkey_listener: keyboard.GlobalHotKeys | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, name="iqassistant-stop-panel", daemon=True)
        self._thread.start()
        self._start_hotkey()

    def stop(self) -> None:
        if self._hotkey_listener is not None:
            self._hotkey_listener.stop()
            self._hotkey_listener = None
        self._queue.put(("close", None))

    def update(self, state: PanelState) -> None:
        self._queue.put(("update", state))

    def show_message(self, message: str) -> None:
        self._queue.put(("message", message))

    def _trigger_stop(self, reason: str) -> None:
        self.logger.warning("Kill switch acionado: %s", reason)
        self.on_stop(reason)
        self.show_message("Automacao parada pelo usuario")

    def _trigger_start(self, reason: str) -> None:
        self.logger.info("Start acionado: %s", reason)
        pin: str | None = None
        if self._root is not None:
            pin = simpledialog.askstring("Validar PIN", "Digite o PIN local para armar a sessao:", parent=self._root, show="*")
        self.on_start(reason, pin)

    def _start_hotkey(self) -> None:
        self._hotkey_listener = keyboard.GlobalHotKeys({
            "<ctrl>+<shift>+a": lambda: self._trigger_start("Hotkey CTRL+SHIFT+A"),
            "<ctrl>+<shift>+s": lambda: self._trigger_stop("Hotkey CTRL+SHIFT+S"),
        })
        self._hotkey_listener.start()

    def _run(self) -> None:
        root = tk.Tk()
        root.title("IQ Assistant Control")
        root.attributes("-topmost", True)
        root.resizable(False, False)
        root.geometry("390x300+30+30")
        root.configure(bg="#111827")

        self._root = root
        self._status_var = tk.StringVar(value="Status: PARADO")
        self._asset_var = tk.StringVar(value="Ativo atual: -")
        self._signal_var = tk.StringVar(value="Proximo sinal: -")
        self._trades_var = tk.StringVar(value="Operacoes na sessao: 0")
        self._integrity_var = tk.StringVar(value="Integridade: NAO GERADA")
        self._pin_var = tk.StringVar(value="PIN: NAO VALIDADO")

        frame = tk.Frame(root, bg="#111827", padx=14, pady=14)
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text="iqoption-assistant", fg="#e5e7eb", bg="#111827", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        tk.Label(frame, textvariable=self._status_var, fg="#93c5fd", bg="#111827", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(10, 0))
        tk.Label(frame, textvariable=self._asset_var, fg="#d1d5db", bg="#111827", font=("Segoe UI", 10)).pack(anchor="w", pady=(8, 0))
        tk.Label(frame, textvariable=self._signal_var, fg="#d1d5db", bg="#111827", font=("Segoe UI", 10), wraplength=300, justify="left").pack(anchor="w", pady=(6, 12))
        tk.Label(frame, textvariable=self._trades_var, fg="#d1d5db", bg="#111827", font=("Segoe UI", 10)).pack(anchor="w", pady=(0, 6))
        tk.Label(frame, textvariable=self._integrity_var, fg="#d1d5db", bg="#111827", font=("Segoe UI", 10)).pack(anchor="w", pady=(0, 6))
        tk.Label(frame, textvariable=self._pin_var, fg="#d1d5db", bg="#111827", font=("Segoe UI", 10)).pack(anchor="w", pady=(0, 12))
        button_row = tk.Frame(frame, bg="#111827")
        button_row.pack(fill="x")
        tk.Button(
            button_row,
            text="START",
            command=lambda: self._trigger_start("Botao START flutuante"),
            bg="#16a34a",
            fg="#ffffff",
            activebackground="#15803d",
            activeforeground="#ffffff",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            padx=18,
            pady=8,
        ).pack(side="left", expand=True, fill="x", padx=(0, 8))
        tk.Button(
            button_row,
            text="STOP",
            command=lambda: self._trigger_stop("Botao STOP flutuante"),
            bg="#dc2626",
            fg="#ffffff",
            activebackground="#b91c1c",
            activeforeground="#ffffff",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            padx=18,
            pady=8,
        ).pack(side="left", expand=True, fill="x", padx=(8, 0))

        root.protocol("WM_DELETE_WINDOW", lambda: self._trigger_stop("Janela STOP fechada"))
        root.after(150, self._drain_queue)
        root.mainloop()

    def _drain_queue(self) -> None:
        if self._root is None:
            return
        try:
            while True:
                action, payload = self._queue.get_nowait()
                if action == "close":
                    self._root.destroy()
                    return
                if action == "update" and isinstance(payload, PanelState):
                    if self._status_var:
                        self._status_var.set(f"Status: {payload.status}")
                    if self._asset_var:
                        self._asset_var.set(f"Ativo atual: {payload.current_asset or '-'}")
                    if self._signal_var:
                        self._signal_var.set(f"Proximo sinal: {payload.next_signal or '-'}")
                    if self._trades_var:
                        self._trades_var.set(f"Operacoes na sessao: {payload.trades_executed}")
                    if self._integrity_var:
                        self._integrity_var.set(f"Integridade: {payload.integrity_status}")
                    if self._pin_var:
                        self._pin_var.set(f"PIN: {payload.pin_status}")
                if action == "message" and isinstance(payload, str) and self._signal_var:
                    self._signal_var.set(payload)
        except Empty:
            pass
        self._root.after(150, self._drain_queue)
