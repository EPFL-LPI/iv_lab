import setuptools

# get __version__
exec(open('iv_lab_controller/_version.py').read())

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="iv-lab-controller",
    version=__version__,
    author="Benjamin Le Geyt <benjamin.legeyt@epfl.ch>, Felix Eickemeyer <felix.eickemeyer@epfl.ch>, Brian Carlsen <carlsen.bri@gmail.com>",
    description="Desktop controller for EPFL's LPI IV Characterization lab.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords=['epfl', 'lpi'],
    url="https://github.com/EPFL-LPI/iv_lab",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)"
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha"
    ],
    python_requires=">=3.6.12, <3.7",
    install_requires=[
        "pyvisa",
        "bric_analysis_libraries>=0.1.2.post1"
    ],
    package_data={
    }
)
