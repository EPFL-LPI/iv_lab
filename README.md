# EPFL LPI | IV Lab

GUI program for running IV lab characterization.

The GUI application is broken into two parts: the **controller** and the **interface**. The controller handles all the business logic for the application, while the interface handles all the view logic.

## Interface
The interface is broken into three major sections

## Controller


### Base classes
Base classes create a common interface for each component of an IV system.

#### Hardware Base
A base class for hardware controllers.

#### Lamp
Defines a common interface for lamp controllers.

#### SMU
Defines a common interface for source meter units (SMUs) that are used for electrical measurements on the cells.

#### Computer Parameters
Holds information about the computer such as the data folder location.

#### IV System Parameters
Holds information about the IV system such as the last calibration date.

#### System
A system represents an entire IV system and how a user can interact with it.
A system consists of a:
+ Lamp,
+ SMU,
+ Computer parameters, and
+ IV System parameters

And can define the available measurements.

#### Result
A base class for measurement results.

### Results
Each type of measurement defined by a system has its own type of `Result` which defines the
measurement parameters and output data. 

#### IV Curve Result
Result of an IV curve measurement. 

#### Chronoamperometry Result
Result of a chronoamperometry measurement.

#### Chronopotentiometry Result
Result of a chronopotentionmetry measurement.

#### MPP Result
Result of an MPP measurement.

## Components


### Lamps


### SMUs


### Computer Parameters


### IV System Parameters


### Systems