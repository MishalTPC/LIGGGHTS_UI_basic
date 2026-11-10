"""LIGGGHTS screen-output telemetry parser.
Author: Mishal Mohanlal | v1.1.1
"""
import re
from dataclasses import dataclass,field

@dataclass
class Metrics:
    phase: str = "Idle"
    step: int | None = None
    particles: int | None = None
    target: int | None = None
    baseline: int | None = None
    percent: float | None = None
    rate: float | None = None
    eta: float | None = None
    meshes: int = 0
    last_mesh: str = "—"
    warnings: int = 0
    diagnostic: str = ""
    thermo: dict = field(default_factory=dict)

class Telemetry:
    def __init__(self, target=None):
        self.data=Metrics(target=target)
        self.columns=[]
        self.prev_step=None
        self.prev_clock=None

    def feed(self,line,now):
        s=line.strip()
        m=self.data
        run=re.match(r"^run\s+(\d+)\b",s,re.I)
        if run:
            m.target=int(run.group(1))
            m.baseline=None
            m.percent=m.eta=m.rate=None
            self.prev_step=self.prev_clock=None
            m.phase="Preparing run"
        if "Setting up run" in s: m.phase="Initializing DEM"
        if "Reading STL file" in s: m.phase="Reading geometry"
        if "Calculating the properties of the given template" in s: m.phase="Generating particle templates"
        mesh=re.search(r"Import and parallelization of mesh\s+(\S+)\s+containing",s,re.I)
        if mesh:
            m.meshes+=1
            m.last_mesh=mesh.group(1)
        if "WARNING:" in s.upper(): m.warnings+=1
        if any(x in s.lower() for x in ("error:", "fatal:", "aborting mpi_comm_world",
                                        "application aborted", "segmentation fault")):
            m.diagnostic=s[:350]
            m.phase="Solver diagnostic"
        words=s.split()
        if len(words)>1 and words[0].lower()=="step" and any(
            x.lower() in ("atoms","temp","press","cpu","ke","kineng") for x in words[1:]):
            self.columns=words
        elif self.columns and len(words)==len(self.columns):
            try:
                step=int(words[0]); float(words[1])
            except (ValueError,IndexError):
                return m
            m.step=step
            m.thermo=dict(zip(self.columns,words))
            for key,value in m.thermo.items():
                if key.lower()=="atoms":
                    try: m.particles=int(float(value))
                    except ValueError: pass
            m.phase="Simulation running"
            if m.baseline is None: m.baseline=step
            if m.target is not None and m.target>0:
                completed=max(0,step-m.baseline)
                m.percent=min(100.,100.*completed/m.target)
                if self.prev_step is not None and self.prev_clock is not None:
                    dt=now-self.prev_clock
                    ds=step-self.prev_step
                    # Buffered multi-line dumps are not reliable timing samples.
                    if dt>=0.5 and ds>0:
                        m.rate=ds/dt
                        m.eta=max(0.,m.target-completed)/m.rate
            self.prev_step=step
            self.prev_clock=now
        if s.startswith("Loop time of"):
            m.phase="Segment complete"
            if m.target is not None: m.percent=100.;m.eta=0.
        return m

def input_target(text):
    runs=re.findall(r"^\s*run\s+(\d+)\b",
                    "\n".join(x.split("#",1)[0] for x in text.splitlines()),re.M|re.I)
    return int(runs[0]) if len(runs)==1 else None

def hms(seconds):
    hours,rest=divmod(max(0,int(seconds)),3600)
    minutes,secs=divmod(rest,60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"

def split_complete_lines(remainder, chunk):
    """Stream line framing: incomplete final lines are held for next poll."""
    buffer = remainder + chunk
    if not buffer:
        return [], ""
    lines = buffer.splitlines(keepends=True)
    if lines and not lines[-1].endswith(("\\r", "\\n")):
        remainder = lines.pop()
    else:
        remainder = ""
    return [line.rstrip("\\r\\n") for line in lines], remainder


def prefer_metrics(console, solver_log):
    """Choose the source with the most complete observed solver data.

    Logs and stdout often contain duplicate lines. Using two independent
    parsers avoids double counting meshes or warnings.
    """
    if solver_log.step is not None and (
        console.step is None or solver_log.step >= console.step
    ):
        return solver_log
    if console.step is not None:
        return console
    if solver_log.diagnostic and not console.diagnostic:
        return solver_log
    if solver_log.meshes > console.meshes:
        return solver_log
    return console
