from setuptools import setup, find_packages
import readalong_studio

setup(
    name='ReadAlong-Studio',
    python_requires='>=3.6',
    version=readalong_studio.VERSION,
    long_description='ReadAlong Studio',
    packages=find_packages(),
    # packages=['readalong_studio'],
    include_package_data=True,
    zip_safe=False,
    install_requires=['flask', 'flask_restful', 'flask_cors']
)