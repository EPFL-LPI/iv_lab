# Build steps
0. Ensure you are using Python 3.6.
1. Install [`fbs`]('https://pypi.org/project/fbs/') if not already.
2. Run `fbs run` to test the app.
3. Run `fbs freeze` to create the executable.
4. Run `fbs installer` to create the installer.

## AttributeError

When building on Ubuntu 21+ an AttributeError will likely be thrown from PyInstaller.
View the discussion [here](https://github.com/mherrmann/fbs/issues/236), and
manually apply the referenced path to the PyInstaller library.
