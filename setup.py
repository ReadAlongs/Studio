import os
from setuptools import setup, find_packages
import readalongs
import datetime as dt

build_no = dt.datetime.today().strftime('%Y%m%d')
version_path = os.path.join(os.path.dirname(readalongs.__file__), '_version.py')
VERSION = readalongs.VERSION + "." + build_no

with open(version_path, 'w') as f:
    f.write(f'__version__ = "{VERSION}"')

with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(
    name='readalongs',
    python_requires='>=3.7',
    version=VERSION,
    long_description='ReadAlong Studio',
    packages=find_packages(exclude=['test']),
    include_package_data=True,
    zip_safe=False,
    install_requires=required,
    entry_points={
        'console_scripts': [
            'readalongs = readalongs.cli:cli'
        ]
    },
)
