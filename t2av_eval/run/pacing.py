"""Per-key pacing shared by every process of a run: at most N generate_content attempts per rolling hour per key.

State is one file per key in <run dir>/.pace/<key id>, holding the time of each attempt in the last hour, under an exclusive
lock (fcntl), so the shards of a run that share a key also share its budget. An attempt waits until a slot is free.
"""
import fcntl, time
from pathlib import Path


class Limiter:
    def __init__(self, path, per_hour, clock=time.time, sleep=time.sleep):
        self.path, self.per_hour, self.clock, self.sleep = Path(path), int(per_hour), clock, sleep
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def acquire(self):
        """block until an attempt is allowed; returns the seconds waited"""
        waited = 0.0
        while True:
            with open(self.path, "a+") as f:
                fcntl.flock(f, fcntl.LOCK_EX)
                f.seek(0)
                now = self.clock()
                ts = [t for t in (float(x) for x in f.read().split()) if t > now - 3600]
                if len(ts) < self.per_hour:
                    ts.append(now)
                    f.seek(0); f.truncate(); f.write("\n".join(f"{t:.3f}" for t in ts) + "\n")
                    return waited
                wait = max(1.0, min(60.0, ts[0] + 3600 - now))
            self.sleep(wait)
            waited += wait

    def count(self):
        now = self.clock()
        if not self.path.exists():
            return 0
        return sum(1 for x in self.path.read_text().split() if float(x) > now - 3600)
