Testing how we can store values, such as first channel, printer head offset, across multiple runs of the program. This feature (especially storing offset) would make it much easier to calibrate everytime we want to run an experiment

### Implementation notes

- The code that made it into `stage.py` is really repetitive and doesn't quite fit
  - A nice fix would be to implement separate classes that can run the checks and 
  - classes inherit from some interface `FileChecker` or `FileHandler` or something
  - implementations (e.g. `OffsetFileChecker`) will store paths and some initial values
  - as well as handle all the methods we have written in stage  