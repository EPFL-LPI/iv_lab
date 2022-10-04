import setuptools


# get __version__
exec( open( 'iv_lab/_version.py' ).read() )

with open("README.md", "r") as fh:
    long_description = fh.read()


project_urls = {
    'Source Code': 'https://github.com/EPFL-LPI/iv_lab',
    'Bug Tracker': 'https://github.com/EPFL-LPI/iv_lab/issues'
}


setuptools.setup(
    name = "iv_lab",
    version = __version__,
    author = "Brian Carlsen",
    author_email = "carlsen.bri@gmail.com",
    description = "Controllers and GUI for IV lab measurements",
    long_description = long_description,
    long_description_content_type = "text/markdown",
    keywords = [ 'iv lab' ],
    url = "",
    project_urls = project_urls,
    packages = setuptools.find_packages(),
    python_requires = '>=3.7',
    classifiers = [
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: Microsoft :: Windows",
        "Development Status :: 3 - Alpha"
    ],
    install_requires = [
        'PyQt6'
        'bric_analysis_libraries>=0.1.2'
    ],
    package_data = {
        'iv_lab': [
        ]
    }
)
