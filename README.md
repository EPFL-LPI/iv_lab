# EPFL LPI | IV Lab

GUI program for running IV lab characterization.

The GUI application is broken into two major parts, each of which has two components.
For more details, see the README of the associated package.

## UI
### Interface
The `interface` package builds the user interface for the application.

### Controller
The `controller` package provides the business logic for the application, as well as provides base classes.

## Hardware
### Instruments
The `instruments` package holds implementations of instrument controllers that can be used to perform experiments.

### Experiments
The `experiments` package creates experiments that can be loaded into the interface for users to run.
