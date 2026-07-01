#!/usr/bin/env python3
"""
Resonarium CLI Skeleton — for Grok CLI hand-off / terminal control
A lightweight TUI param editor + state exporter. 
No real-time audio (the HTML version excels at that), but perfect for scripting, 
batch preset creation, or exporting JSON that the enhanced web app can consume 
(if you extend loadState to accept URL/import).

Run: python3 resonarium_cli_skeleton.py
Requires: pip install rich   (beautiful tables + live console)

Commands in the loop:
  t s1          -> toggle sweep 1 on/off
  t b3          -> toggle binaural 3
  t tone4       -> toggle single tone 4
  set s2 f 880  -> set sweep 2 center freq
  set b1 beat 4.5
  set tone0 lvl 0.4
  emerge        -> nudge active (like web EMERGE)
  preset fractal
  show          -> reprint tables
  export state.json
  quit
"""

from __future__ import annotations
import json
import random
import sys
from dataclasses import dataclass, asdict
from typing import List

try:
    from rich.console import Console
    from rich.table import Table
    from rich.prompt import Prompt
    from rich import print as rprint
except ImportError:
    print("Please: pip install rich")
    sys.exit(1)

console = Console()

PHI = 1.6180339887

@dataclass
class Sweep:
    f: float = 1024.0
    width: float = 60.0
    pass_: float = 0.5
    shape: str = "up"
    wave: str = "sine"
    lvl: float = 0.35
    on: bool = True

@dataclass
class Bin:
    carrier: float = 128.0
    beat: float = 2.0
    wave: str = "sine"
    lvl: float = 0.34
    on: bool = True

@dataclass
class Single:
    f: float = 256.0
    wave: str = "sine"
    lvl: float = 0.38
    on: bool = True

class ResonariumCLI:
    def __init__(self):
        self.sweeps: List[Sweep] = [
            Sweep(f=1024, width=60, pass_=0.5, shape="up", wave="sine", lvl=0.35, on=True),
            Sweep(f=1100, width=90, pass_=0.33, shape="down", wave="sine", lvl=0.30, on=False),
            Sweep(f=1200, width=120, pass_=0.8, shape="up", wave="saw", lvl=0.28, on=False),
            Sweep(f=1300, width=80, pass_=0.22, shape="down", wave="square", lvl=0.26, on=False),
        ]
        self.bins: List[Bin] = [
            Bin(carrier=128, beat=2, wave="sine", lvl=0.34, on=True),
            Bin(carrier=160, beat=2, wave="sine", lvl=0.32, on=False),
            Bin(carrier=200, beat=3, wave="sine", lvl=0.30, on=False),
            Bin(carrier=256, beat=4, wave="sine", lvl=0.30, on=True),
            Bin(carrier=320, beat=5, wave="sine", lvl=0.28, on=False),
            Bin(carrier=400, beat=8, wave="sine", lvl=0.26, on=False),
        ]
        self.singles: List[Single] = [
            Single(f=256, wave="sine", lvl=0.38, on=True),
            Single(f=341.3, wave="sine", lvl=0.32, on=False),
            Single(f=426.6, wave="saw", lvl=0.30, on=False),
            Single(f=512, wave="sine", lvl=0.30, on=False),
            Single(f=639, wave="saw", lvl=0.28, on=False),
            Single(f=768, wave="sine", lvl=0.26, on=False),
        ]
        self.compound = True
        self.master = 0.22

    def show(self):
        console.rule("[bold cyan]RESONARIUM — CLI Skeleton[/bold cyan]")
        # Sweeps
        t1 = Table(title="Sweep Field (LFO glides)", show_header=True, header_style="bold yellow")
        t1.add_column("S#", style="dim"); t1.add_column("On", justify="center")
        t1.add_column("Center Hz", justify="right"); t1.add_column("±Width"); t1.add_column("Pass")
        t1.add_column("Shape"); t1.add_column("Wave"); t1.add_column("Lvl")
        for i, s in enumerate(self.sweeps):
            t1.add_row(str(i), "●" if s.on else "○", f"{s.f:.0f}", f"±{s.width:.0f}",
                       f"{s.pass_:.2f}s", s.shape, s.wave, f"{s.lvl*100:.0f}%")
        console.print(t1)

        # Binaural
        t2 = Table(title="Binaural Cascade (headphones!)", show_header=True, header_style="bold cyan")
        t2.add_column("B#", style="dim"); t2.add_column("On", justify="center")
        t2.add_column("Carrier Hz"); t2.add_column("Beat Hz"); t2.add_column("Wave"); t2.add_column("Lvl")
        for i, b in enumerate(self.bins):
            eff_beat = b.beat
            if self.compound:
                eff_beat = sum(bb.beat for bb in self.bins[:i+1])
            t2.add_row(str(i), "●" if b.on else "○", f"{b.carrier:.0f}",
                       f"{eff_beat:.2f}", b.wave, f"{b.lvl*100:.0f}%")
        console.print(t2)

        # Singles
        t3 = Table(title="Single Tones (knob dials)", show_header=True, header_style="bold magenta")
        t3.add_column("T#", style="dim"); t3.add_column("On", justify="center")
        t3.add_column("Freq Hz", justify="right"); t3.add_column("Wave"); t3.add_column("Lvl")
        for i, s in enumerate(self.singles):
            t3.add_row(str(i), "●" if s.on else "○", f"{s.f:.1f}", s.wave, f"{s.lvl*100:.0f}%")
        console.print(t3)
        console.print(f"[dim]Compound:[/dim] {'on' if self.compound else 'off'}   [dim]Master:[/dim] {self.master*100:.0f}%")
        console.print("[dim]Commands: t s0 | set b2 beat 5.5 | emerge | preset fractal | export state.json | quit[/dim]\n")

    def toggle(self, which: str, idx: int):
        if which == "s" and 0 <= idx < len(self.sweeps):
            self.sweeps[idx].on = not self.sweeps[idx].on
        elif which == "b" and 0 <= idx < len(self.bins):
            self.bins[idx].on = not self.bins[idx].on
        elif which == "tone" and 0 <= idx < len(self.singles):
            self.singles[idx].on = not self.singles[idx].on
        else:
            rprint("[red]Invalid toggle target[/red]")

    def set_param(self, which: str, idx: int, param: str, val: float):
        try:
            if which == "s" and 0 <= idx < len(self.sweeps):
                setattr(self.sweeps[idx], param if param != "pass" else "pass_", val)
            elif which == "b" and 0 <= idx < len(self.bins):
                setattr(self.bins[idx], param, val)
            elif which == "tone" and 0 <= idx < len(self.singles):
                setattr(self.singles[idx], param, val)
            else:
                rprint("[red]Bad target[/red]")
        except Exception as e:
            rprint(f"[red]Set error: {e}[/red]")

    def emerge(self, amt: float = 0.028):
        did = False
        for s in self.sweeps:
            if s.on:
                s.f *= (1 + (random.random()-0.5)*amt*0.6)
                s.f = max(55, min(1950, s.f))
                s.width *= (1 + (random.random()-0.5)*amt*1.1)
                s.width = max(4, min(380, s.width))
                did = True
        for b in self.bins:
            if b.on:
                b.beat *= (1 + (random.random()-0.5)*amt*1.3)
                b.beat = max(0.25, min(38, b.beat))
                did = True
        for s in self.singles:
            if s.on:
                s.f *= (1 + (random.random()-0.5)*amt*0.45)
                s.f = max(48, min(1950, s.f))
                did = True
        if did:
            rprint("[yellow]✧ Emergent nudge applied — patterns evolving[/yellow]")

    def load_preset(self, name: str):
        if name == "fractal":
            self.sweeps[0].on = True; self.sweeps[0].f = 110; self.sweeps[0].width = PHI*28; self.sweeps[0].pass_ = PHI*1.8
            self.sweeps[1].on = True; self.sweeps[1].f = round(110*PHI); self.sweeps[1].width = PHI*19; self.sweeps[1].pass_ = PHI*2.6
            self.sweeps[3].on = True; self.sweeps[3].f = round(110*PHI*PHI); self.sweeps[3].width = PHI*32; self.sweeps[3].pass_ = PHI*0.9
            self.bins[0].on = True; self.bins[0].carrier = 144; self.bins[0].beat = PHI*2.1
            self.bins[4].on = True; self.bins[4].carrier = 233; self.bins[4].beat = PHI*3.4
            self.singles[0].on = True; self.singles[0].f = 89
            self.singles[5].on = True; self.singles[5].f = round(89*PHI*PHI)
            rprint("[magenta]Fractal Unfold preset loaded (golden self-similarity)[/magenta]")
        elif name == "theta":
            for s in self.sweeps: s.on = False
            self.sweeps[0].on = True; self.sweeps[0].f = 68; self.sweeps[0].pass_ = 11
            self.sweeps[1].on = True; self.sweeps[1].f = 94; self.sweeps[1].pass_ = 7.5
            for b in self.bins: b.on = False
            self.bins[0].on = True; self.bins[0].carrier = 180; self.bins[0].beat = 4.2
            self.bins[2].on = True; self.bins[2].carrier = 260; self.bins[2].beat = 5.8
            for s in self.singles: s.on = False
            self.singles[0].on = True; self.singles[0].f = 96
            self.singles[3].on = True; self.singles[3].f = 192
            rprint("[cyan]Theta Drift loaded[/cyan]")
        # add alpha / void similarly if wanted
        else:
            rprint("[yellow]Preset not implemented in skeleton (see web version)[/yellow]")

    def export(self, path: str):
        state = {
            "sweeps": [asdict(s) for s in self.sweeps],
            "bins": [asdict(b) for b in self.bins],
            "singles": [asdict(s) for s in self.singles],
            "compound": self.compound,
            "masterVol": self.master,
        }
        with open(path, "w") as f:
            json.dump(state, f, indent=2)
        rprint(f"[green]Exported to {path} — load in enhanced web app if you extend persistence[/green]")

    def run(self):
        self.show()
        while True:
            try:
                cmd = Prompt.ask("[bold]resonarium>[/bold]", default="show").strip().lower()
                if cmd in ("q", "quit", "exit"):
                    break
                if cmd == "show":
                    self.show()
                    continue
                if cmd.startswith("t "):
                    parts = cmd.split()
                    if len(parts) == 2:
                        tgt = parts[1]
                        if tgt.startswith("s"): self.toggle("s", int(tgt[1:]))
                        elif tgt.startswith("b"): self.toggle("b", int(tgt[1:]))
                        elif tgt.startswith("tone"): self.toggle("tone", int(tgt[4:]))
                        self.show()
                    continue
                if cmd.startswith("set "):
                    # set s2 f 880   or set b1 beat 4.5
                    parts = cmd.split()
                    if len(parts) >= 4:
                        tgt, param, val = parts[1], parts[2], float(parts[3])
                        if tgt.startswith("s"): self.set_param("s", int(tgt[1:]), param, val)
                        elif tgt.startswith("b"): self.set_param("b", int(tgt[1:]), param, val)
                        elif tgt.startswith("tone"): self.set_param("tone", int(tgt[4:]), param, val)
                        self.show()
                    continue
                if cmd == "emerge":
                    self.emerge()
                    self.show()
                    continue
                if cmd.startswith("preset "):
                    self.load_preset(cmd.split()[1])
                    self.show()
                    continue
                if cmd.startswith("export "):
                    self.export(cmd.split()[1])
                    continue
                if cmd == "help":
                    rprint("t s0 / t b2 / t tone3   |  set s1 f 440   |  emerge   |  preset fractal   |  export state.json")
                    continue
                rprint("[dim]Unknown. Try: show, t s0, set b1 beat 5, emerge, preset fractal, export foo.json, quit[/dim]")
            except (ValueError, IndexError, KeyboardInterrupt):
                rprint("[red]Bad input or interrupt[/red]")
                continue

if __name__ == "__main__":
    ResonariumCLI().run()
