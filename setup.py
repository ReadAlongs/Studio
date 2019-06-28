from setuptools import setup, find_packages
import readalongs

with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(
    name='ReadAlong-Studio',
    python_requires='>=3.6',
    version=readalongs.VERSION,
    long_description='ReadAlong Studio',
    packages=find_packages(exclude=['test']),
    include_package_data=True,
    zip_safe=False,
    install_requires=required,
    entry_points={
        'console_scripts': [
            'readalongs_align = readalongs.align:main',
            'readalongs_create_epub = readalongs.epub.create_epub:main',
        ]
    },
)
