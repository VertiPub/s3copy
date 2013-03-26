from setuptools import setup

setup(
    name='s3copy',
    version='0.0.2',
    author='Donald "Max" Ziff',
    author_email='ziff@verticloud.com',
    scripts=['s3copy'],
    url='http://pypi.python.org/pypi/S3Copy/',
    license='LICENSE.txt',
    description='Multi-threaded, fault-tolerant, bucket-to-bucket copy for s3.',
    long_description=open('README.rst').read(),
    install_requires=[
        "boto >= 2.8.0",
        "argparse >= 1.2.1",
    ],
)
