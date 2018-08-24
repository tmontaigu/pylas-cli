from setuptools import setup

setup(
    name='pylas-cli',
    version='0.1.0',
    packages=['pylascli'],
    url='',
    license='MIT',
    author='t.montaigu',
    author_email='',
    description='',
    entry_points={
        "console_scripts": [
            "pylas=pylascli.main:cli"

        ]

    }
)
