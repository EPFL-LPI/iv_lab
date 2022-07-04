# Build steps

## Initial setup
This project uses [`fbs`]('https://pypi.org/project/fbs/') to build an executable from the project.
To get setup with `fbs` there are some initial setup steps to take.
+ Check if a [virtual environment](https://docs.python.org/3/library/venv.html) exists for you system.
	Virtual environments are named `.venv-<system_name>`, so may be hidden on your file browser.
	Be sure that hidden files are being shown.
+ If a virtual environment for your system does not yet exist, you can create it using
	the [`venv`](https://docs.python.org/3/library/venv.html) Python module.
	You must use Python 3.6.12 or greater to create the virtual environment.
	You can check your Python version by running `python --version` from the command line.
	You can specify which version of Python is used by appending the major and minor version
	to the Python command.
	e.g. `python3.6`.
	Be sure to follow the naming convention of `.venv-<system_name>` where `<system_name>`
	describes the operating system and version of your machine.

## Running the program
1. Ensure that no other virtual environments are active. For instance, if Anaconda is
	installed you can deactivate it using `conda deactivate`.
2. Activate the virtual environment corresponding to your machine.
	+ For Unix-based systems (Linux, Mac, etc.) run `source .venv-<system_name>/bin/activate`
	+ For Windows machines run `call .venv-<system_name>/Scripts/activate`
3. Call `fbs run`.
	+ The program must be closed and restarted to incorporate changes.

## Building the program
1. Ensure package versions are updated.
2. To build the program into an executable run `fbs freeze`.
3. Run `fbs installer` to create the installer.
4. All the relevant files will be placed in the `target` folder.
	Move these files into the corresponding `target-<system_name>` folder.

## AttributeError

When building on Ubuntu 21+ an AttributeError will likely be thrown from PyInstaller.
View the discussion [here](https://github.com/mherrmann/fbs/issues/236), and
manually apply the referenced path to the PyInstaller library.
