import datetime as dt
import os

from setuptools import find_packages, setup

import readalongs

build_no = dt.datetime.today().strftime("%Y%m%d")
version_path = os.path.join(os.path.dirname(readalongs.__file__), "_version.py")
VERSION = readalongs.VERSION + "." + build_no

with open(version_path, "w", newline="\n", encoding="utf-8") as f:
    print(f'__version__ = "{VERSION}"', file=f)

with open("requirements.min.txt", encoding="utf8") as f:
    required = f.read().splitlines()

this_directory = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(this_directory, "README.md"), encoding="utf8") as f:
    long_description = f.read()

setup(
    name="readalongs",
    license="MIT",
    python_requires=">=3.7",
    version=VERSION,
    description="ReadAlong Studio",
    url="https://github.com/ReadAlongs/Studio",
    long_description=long_description,
    long_description_content_type="text/markdown",
    platform=["any"],
    packages=find_packages(exclude=["test"]),
    include_package_data=True,
    zip_safe=False,
    install_requires=required,
    entry_points={"console_scripts": ["readalongs = readalongs.cli:cli"]},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
