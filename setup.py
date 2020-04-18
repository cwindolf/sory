from setuptools import find_packages, setup
import sory

setup(
    name='sory',
    version=sory.__version__,
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'flask',
    ],
)

