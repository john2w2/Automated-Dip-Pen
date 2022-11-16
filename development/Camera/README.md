# Camera Development
For figuring out how pymmcore works, how to manage camera resources effectively, how to make usage robust for the experimenter

---
## future stuff:
- should make camera singleton
  - this means the current camera is easy to access from anwhere, without needing to pass references everywhere
  - Also prevents trying to connect to busy camera in GUI
- interface for cameras, then make classes for CoolSnap, OrcaFlash, etc.
- Figure out why orca flash crashes
- figure out how continuous sequence acquisition should be managed

