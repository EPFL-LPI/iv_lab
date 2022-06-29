import setuptools

# get __version__
exec(open('iv_lab_interface/_version.py').read())

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="iv-lab-interface",
    version=__version__,
    author="Benjamin Le Geyt <benjamin.legeyt@epfl.ch>, Felix Eickemeyer <felix.eickemeyer@epfl.ch>, Brian Carlsen <carlsen.bri@gmail.com>",
    description="Desktop interface for EPFL's LPI IV Characterization lab.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords=['epfl', 'lpi'],
    url="",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)"
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha"
    ],
    python_requires=">=3.6.12, <3.7.0",
    install_requires=[
        'PyQt5==5.9.2',  # version requirement for fbs, use Python 3.6
        'pyqtgraph',
        'pandas',
        'matplotlib',
        'iv-lab-controller>=0.7.0'
    ],
    package_data={
    }
)
