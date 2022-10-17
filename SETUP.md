# Setup

This guide will walk you through how to setup the `IV Lab` program for the first
time.

## Users
A `users.json` file stores all user credentials and permissions.
To begin, create a `users.json` file in your computer's application data folder
for the IV Lab program.
This location can be found by referencing the `AppDataLocation` in the
[`PyQt6.QtCore.QStandardPaths` documentation](https://doc.qt.io/qtforpython/PySide6/QtCore/QStandardPaths.html).

### Schema
The `users.json` file is a list of `User`s where each `User` consists of a
+ `username` (str)
+ `password` (str)
+ `permissions` ([str]) with valid values listed below.

#### Example
```json
[
    {
        "username": "user",
        "password": "user",
        "permissions": ["basic"]
    },
    {
        "username": "admin",
        "password": "admin",
        "permissions": ["basic", "admin"]
    }
]
```

### Permissions
User permissions indicate which actions a user is capable of performing.
+ `basic`: Run standard measurement programs.
+ `admin`: Configure settings and run administrative measurement programs.

# Developers
## Installing packages
To run the `IV Lab` application four packages should be installed:
1. `iv_lab_controller` (required)
2. `iv_lab_interface` (required)
3. `iv_lab_instruments`
4. `iv_lab_experiments`

For packaging the application into an executable [`fbs`](https://build-system.fman.io/) is used.