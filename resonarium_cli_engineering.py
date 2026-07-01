#!/usr/bin/env python3
"""
Resonarium CLI Engineering Companion
Terminal parameter editor, metrics analyzer, preset builder, JSON importer/exporter.
The exported schema matches resonarium_engineering_platform.html.

Install:  python3 -m pip install rich
Run:      python3 resonarium_cli_engineering.py
Commands:
  show / metrics / help
  t s0 | t b2 | t tone3
  set s1 f 880 | set s1 pass 0.25 | set b0 beat 4.5 | set tone3 lvl 0.4
  set compound on | set master 0.30 | set title "Study"
  compound [on|off|toggle] | master 30 | panic | alloff
  title "My resonance" | tags "theta fractal" | notes "..."
  preset theta|alpha|fractal|void|solfeggio|crystal
  emerge [amount]
  phi | normalize
  import state.json
  export state.json
  quit
"""
from __future__ import annotations
import json, math, random, shlex, sys
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.prompt import Prompt
except ImportError:
    print("Please install rich first: python3 -m pip install rich")
    sys.exit(1)

PHI = 1.618033988749895
SCHEMA = "resonarium.state.v2"
console = Console()

@dataclass
class Sweep:
    f: float = 1024.0
    width: float = 60.0
    pass_: float = 0.5
    shape: str = "up"
    wave: str = "sine"
    lvl: float = 0.35
    on: bool = True
    def to_json(self) -> Dict[str, Any]:
        d = asdict(self); d["pass"] = d.pop("pass_"); return d

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

@dataclass
class Manifest:
    title: str = "CLI resonance study"
    tags: str = "cli, engineering"
    notes: str = ""

class ResonariumCLI:
    def __init__(self) -> None:
        self.sweeps: List[Sweep] = [
            Sweep(1024,60,.5,"up","sine",.35,True), Sweep(1100,90,.33,"down","sine",.30,False),
            Sweep(1200,120,.8,"up","saw",.28,False), Sweep(1300,80,.22,"down","square",.26,False),
        ]
        self.bins: List[Bin] = [
            Bin(128,2,"sine",.34,True), Bin(160,2,"sine",.32,False), Bin(200,3,"sine",.30,False),
            Bin(256,4,"sine",.30,True), Bin(320,5,"sine",.28,False), Bin(400,8,"sine",.26,False),
        ]
        self.singles: List[Single] = [
            Single(256,"sine",.38,True), Single(341.3,"sine",.32,False), Single(426.6,"saw",.30,False),
            Single(512,"sine",.30,False), Single(639,"saw",.28,False), Single(768,"sine",.26,False),
        ]
        self.compound = True
        self.masterVol = 0.22
        self.view = "field"
        self.manifest = Manifest()

    def band(self, b: float) -> str:
        return "delta" if b < 4 else "theta" if b < 8 else "alpha" if b < 13 else "beta" if b < 30 else "gamma"

    def eff_bins(self) -> List[Dict[str, float | str]]:
        total = 0.0; out = []
        for i, b in enumerate(self.bins):
            beat, lvl = b.beat, b.lvl
            if self.compound:
                total += b.beat
                beat = total
                lvl = min(1.0, b.lvl * (0.6 + 0.16 * i))
            out.append({"beat": beat, "lvl": lvl, "band": self.band(float(beat))})
        return out

    def show(self) -> None:
        console.rule("[bold cyan]RESONARIUM ENGINEERING CLI[/bold cyan]")
        t = Table(title="Sweep Field", header_style="bold yellow")
        for col in ["S#","On","Center Hz","±Width","Pass","Shape","Wave","Lvl"]: t.add_column(col)
        for i,s in enumerate(self.sweeps):
            t.add_row(str(i), "●" if s.on else "○", f"{s.f:.2f}", f"±{s.width:.2f}", f"{s.pass_:.5f}s", s.shape, s.wave, f"{s.lvl:.2f}")
        console.print(t)
        e = self.eff_bins()
        t = Table(title="Binaural Cascade", header_style="bold cyan")
        for col in ["B#","On","Carrier","Beat","Effective","Band","Wave","Lvl"]: t.add_column(col)
        for i,b in enumerate(self.bins):
            t.add_row(str(i), "●" if b.on else "○", f"{b.carrier:.2f}", f"{b.beat:.2f}", f"{float(e[i]['beat']):.2f}", str(e[i]["band"]), b.wave, f"{b.lvl:.2f}")
        console.print(t)
        t = Table(title="Single Tones", header_style="bold magenta")
        for col in ["T#","On","Freq","Wave","Lvl"]: t.add_column(col)
        for i,s in enumerate(self.singles):
            t.add_row(str(i), "●" if s.on else "○", f"{s.f:.2f}", s.wave, f"{s.lvl:.2f}")
        console.print(t)
        console.print(f"[dim]Compound:[/dim] {'on' if self.compound else 'off'}   [dim]Master:[/dim] {self.masterVol:.2f}   [dim]View:[/dim] {self.view}")
        if self.manifest.title or self.manifest.tags or self.manifest.notes:
            console.print(f"[dim]Title:[/dim] {self.manifest.title or '(untitled)'}   [dim]Tags:[/dim] {self.manifest.tags or ''}")
        self.metrics()

    def metrics(self) -> None:
        eff = self.eff_bins()
        freqs: List[float] = []
        freqs += [s.f for s in self.sweeps if s.on]
        for i,b in enumerate(self.bins):
            if b.on:
                freqs += [b.carrier, b.carrier + float(eff[i]["beat"])]
        freqs += [s.f for s in self.singles if s.on]
        active = sum(s.on for s in self.sweeps) + sum(b.on for b in self.bins) + sum(s.on for s in self.singles)
        gain_sum = sum(s.lvl for s in self.sweeps if s.on) + sum(b.lvl for b in self.bins if b.on) + sum(s.lvl for s in self.singles if s.on)
        bands = {"delta":0,"theta":0,"alpha":0,"beta":0,"gamma":0}
        for i,b in enumerate(self.bins):
            if b.on: bands[str(eff[i]["band"])] += 1
        risk = "hot" if self.masterVol > .55 or gain_sum > 4.5 else "watch" if self.masterVol > .35 or gain_sum > 3 else "safe"
        msg = f"voices={active}  range={min(freqs) if freqs else 0:.1f}-{max(freqs) if freqs else 0:.1f}Hz  gain_sum={gain_sum:.2f}  risk={risk}  bands={bands}"
        console.print(Panel(msg, title="Live Analyzer", border_style="green" if risk == "safe" else "yellow" if risk == "watch" else "red"))

    def toggle(self, target: str) -> None:
        t = target.lower()
        if t.startswith("tone"):
            idx = int(t[4:]); self.singles[idx].on = not self.singles[idx].on; return
        group, idx = t[0], int(t[1:])
        if group == "s": self.sweeps[idx].on = not self.sweeps[idx].on
        elif group == "b": self.bins[idx].on = not self.bins[idx].on
        else: raise ValueError("target must be s#, b#, or tone#")

    def set_param(self, target: str, param: str, value: str) -> None:
        tgt = target.lower()
        if tgt == "compound":
            self.compound = value.lower() in ("1","true","on","yes")
            return
        if tgt == "master":
            v = float(value)
            if v > 1: v /= 100
            self.masterVol = max(0.0, min(1.0, v))
            return
        if tgt == "title":
            self.manifest.title = value.strip("\"'")
            return
        if tgt == "tags":
            self.manifest.tags = value.strip("\"'")
            return
        if tgt == "notes":
            self.manifest.notes = value.strip("\"'")
            return
        if tgt.startswith("tone"):
            obj: Any = self.singles[int(target[4:])]
        elif tgt.startswith("s"):
            obj = self.sweeps[int(target[1:])]
            if param == "pass": param = "pass_"
        elif tgt.startswith("b"):
            obj = self.bins[int(target[1:])]
        else:
            raise ValueError("bad target")
        if param in ("on",):
            setattr(obj, param, value.lower() in ("1","true","on","yes"))
        elif param in ("wave","shape"):
            setattr(obj, param, value)
        else:
            setattr(obj, param, float(value))

    def emerge(self, amt: float = .028) -> None:
        for s in self.sweeps:
            if s.on:
                s.f = max(40, min(2200, s.f * (1 + (random.random() - .5) * amt * .6)))
                s.width = max(3, min(600, s.width * (1 + (random.random() - .5) * amt * 1.1)))
        for b in self.bins:
            if b.on:
                b.beat = max(.1, min(60, b.beat * (1 + (random.random() - .5) * amt * 1.3)))
        for s in self.singles:
            if s.on:
                s.f = max(40, min(2200, s.f * (1 + (random.random() - .5) * amt * .45)))
        console.print("[yellow]Emergent nudge applied.[/yellow]")

    def all_off(self) -> None:
        for collection in (self.sweeps, self.bins, self.singles):
            for x in collection: x.on = False

    def preset(self, name: str) -> None:
        self.all_off()
        if name == "theta":
            self.sweeps[0] = Sweep(68,22,11,"up","sine",.42,True); self.sweeps[1] = Sweep(94,15,7.5,"down","sine",.36,True)
            self.bins[0] = Bin(180,4.2,"sine",.38,True); self.bins[2] = Bin(260,5.8,"sine",.32,True)
            self.singles[0] = Single(96,"sine",.22,True); self.singles[3] = Single(192,"sine",.18,True)
        elif name == "alpha":
            self.sweeps[2] = Sweep(220,35,4.5,"up","saw",.28,True)
            self.bins[1] = Bin(320,9.5,"sine",.36,True); self.bins[3] = Bin(410,10.8,"sine",.30,True)
            self.singles[1] = Single(256,"sine",.25,True); self.singles[2] = Single(341,"saw",.22,True)
        elif name == "fractal":
            self.sweeps[0] = Sweep(110,PHI*28,PHI*1.8,"up","sine",.38,True)
            self.sweeps[1] = Sweep(round(110*PHI),PHI*19,PHI*2.6,"down","sine",.33,True)
            self.sweeps[3] = Sweep(round(110*PHI*PHI),PHI*32,PHI*.9,"up","saw",.29,True)
            self.bins[0] = Bin(144,PHI*2.1,"sine",.35,True); self.bins[4] = Bin(233,PHI*3.4,"sine",.28,True)
            self.singles[0] = Single(89,"sine",.30,True); self.singles[5] = Single(round(89*PHI*PHI),"sine",.24,True)
        elif name == "void":
            self.sweeps[0] = Sweep(52,12,22,"down","sine",.45,True)
            self.bins[0] = Bin(110,2.8,"sine",.40,True); self.singles[0] = Single(55,"sine",.35,True)
        elif name == "solfeggio":
            for i,f in enumerate([174,285,396,528]): self.sweeps[i] = Sweep(f,12+8*i,3+i,"down" if i%2 else "up","sine",.24,i<3)
            for i,bt in enumerate([3.96,5.28,8.52]): self.bins[i] = Bin([174,285,396][i],bt,"sine",.25,True)
            for i,f in enumerate([174,285,396,528,639,852]): self.singles[i] = Single(f,"sine",.18,i<4)
        elif name == "crystal":
            for i,f in enumerate([192,256,384,512]): self.sweeps[i] = Sweep(f,8*(i+1),1.5+i*.75,"sine","saw" if i==2 else "sine",.20,True)
            for i,bt in enumerate([6,9,12,15]): self.bins[i] = Bin(192+i*64,bt,"sine",.22,True)
            for i,f in enumerate([128,192,256,384,512,768]): self.singles[i] = Single(f,"sine",.16,True)
        else:
            raise ValueError("unknown preset")
        console.print(f"[magenta]Preset loaded: {name}[/magenta]")

    def phi(self) -> None:
        base = 89
        for i,s in enumerate(self.sweeps):
            s.f = base * (PHI ** (i+1)); s.width = 13 * (PHI ** i); s.pass_ = (i+1) * PHI; s.on = i != 2
        for i,b in enumerate(self.bins):
            b.carrier = base * (PHI ** (1+i/2)); b.beat = (i+1) * PHI; b.on = i < 4; b.wave = "sine"
        for i,s in enumerate(self.singles):
            s.f = base * (PHI ** (i/2)); s.on = i < 5; s.wave = "sine"
        console.print("[cyan]φ tune applied.[/cyan]")

    def normalize(self) -> None:
        active = [*filter(lambda x: x.on, self.sweeps), *filter(lambda x: x.on, self.bins), *filter(lambda x: x.on, self.singles)]
        target = min(.42, 1 / max(1, math.sqrt(len(active))) * .62)
        for x in active: x.lvl = min(x.lvl, target)
        console.print(f"[green]Normalized active levels to <= {target:.3f}[/green]")

    def state(self) -> Dict[str, Any]:
        return {
            "schema": SCHEMA,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "sweeps": [s.to_json() for s in self.sweeps],
            "bins": [asdict(b) for b in self.bins],
            "singles": [asdict(s) for s in self.singles],
            "compound": self.compound,
            "masterVol": self.masterVol,
            "view": self.view,
            "manifest": asdict(self.manifest),
        }

    def apply_state(self, st: Dict[str, Any]) -> None:
        for i,d in enumerate(st.get("sweeps", [])[:4]):
            self.sweeps[i] = Sweep(f=d.get("f",1024), width=d.get("width",60), pass_=d.get("pass",d.get("pass_",.5)), shape=d.get("shape","up"), wave=d.get("wave","sine"), lvl=d.get("lvl",.35), on=d.get("on",True))
        for i,d in enumerate(st.get("bins", [])[:6]): self.bins[i] = Bin(**{k:d.get(k, getattr(self.bins[i],k)) for k in asdict(self.bins[i])})
        for i,d in enumerate(st.get("singles", [])[:6]): self.singles[i] = Single(**{k:d.get(k, getattr(self.singles[i],k)) for k in asdict(self.singles[i])})
        self.compound = bool(st.get("compound", self.compound)); self.masterVol = float(st.get("masterVol", self.masterVol)); self.view = st.get("view", self.view)
        man = st.get("manifest", {}) or {}; self.manifest = Manifest(man.get("title", self.manifest.title), man.get("tags", self.manifest.tags), man.get("notes", self.manifest.notes))

    def export(self, path: str) -> None:
        Path(path).write_text(json.dumps(self.state(), indent=2), encoding="utf-8")
        console.print(f"[green]Exported {path}[/green]")

    def import_file(self, path: str) -> None:
        self.apply_state(json.loads(Path(path).read_text(encoding="utf-8")))
        console.print(f"[green]Imported {path}[/green]")

    def help(self) -> None:
        console.print(__doc__ or "")

    def run(self) -> None:
        self.show()
        while True:
            try:
                cmd = Prompt.ask("[bold]resonarium>[/bold]", default="show").strip()
                if not cmd: continue
                try:
                    parts = shlex.split(cmd)
                except Exception:
                    parts = cmd.split()
                head = parts[0].lower()
                if head in {"q","quit","exit"}: break
                if head == "show": self.show(); continue
                if head == "metrics": self.metrics(); continue
                if head == "help": self.help(); continue
                if head == "t" and len(parts) == 2: self.toggle(parts[1]); self.show(); continue
                if head == "set" and len(parts) >= 3:
                    tgt = parts[1].lower()
                    if tgt in ("compound", "master", "title", "tags", "notes"):
                        val = " ".join(parts[2:])
                        self.set_param(tgt, "", val)
                        self.show()
                        continue
                    elif len(parts) >= 4:
                        self.set_param(parts[1], parts[2], parts[3])
                        self.show()
                        continue
                    else:
                        console.print("[dim]set usage: set s1 f 440 | set b0 beat 4.5 | set title My Study | set master 0.3[/dim]")
                        continue
                if head == "preset" and len(parts) == 2: self.preset(parts[1].lower()); self.show(); continue
                if head == "emerge": self.emerge(float(parts[1]) if len(parts)>1 else .028); self.show(); continue
                if head == "phi": self.phi(); self.show(); continue
                if head == "normalize": self.normalize(); self.show(); continue
                if head == "export" and len(parts) == 2: self.export(parts[1]); continue
                if head == "import" and len(parts) == 2: self.import_file(parts[1]); self.show(); continue
                if head in ("panic", "alloff", "all-off"):
                    self.all_off()
                    self.show()
                    continue
                if head == "compound":
                    if len(parts) > 1:
                        arg = parts[1].lower()
                        if arg == "toggle":
                            self.compound = not self.compound
                        else:
                            self.compound = arg in ("1", "true", "on", "yes")
                    else:
                        self.compound = not self.compound
                    console.print(f"[cyan]compound = {'on' if self.compound else 'off'}[/cyan]")
                    self.show()
                    continue
                if head == "master" and len(parts) >= 2:
                    val = float(parts[1])
                    if val > 1: val /= 100
                    self.masterVol = max(0.0, min(1.0, val))
                    console.print(f"[cyan]masterVol = {self.masterVol:.2f}[/cyan]")
                    self.show()
                    continue
                if head == "title" and len(parts) >= 2:
                    self.manifest.title = " ".join(parts[1:]).strip("\"'")
                    console.print(f"[cyan]title = {self.manifest.title}[/cyan]")
                    continue
                if head == "tags" and len(parts) >= 2:
                    self.manifest.tags = " ".join(parts[1:]).strip("\"'")
                    console.print(f"[cyan]tags = {self.manifest.tags}[/cyan]")
                    continue
                if head == "notes":
                    self.manifest.notes = " ".join(parts[1:]).strip("\"'") if len(parts) > 1 else ""
                    console.print(f"[cyan]notes updated[/cyan]")
                    continue
                if head in ("factory", "reset", "factory-reset"):
                    self.__init__()
                    console.print("[yellow]Factory defaults restored.[/yellow]")
                    self.show()
                    continue
                console.print("[dim]Unknown command. Try help.[/dim]")
            except KeyboardInterrupt:
                console.print("\n[red]Interrupted.[/red]")
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")

if __name__ == "__main__":
    ResonariumCLI().run()
