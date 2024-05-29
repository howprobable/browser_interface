from setuptools import setup, find_packages

setup(
    name='browser_interface',
    version='1.0.0',
    packages=find_packages(),
    description='A python interface for a browser',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='Jannik Eggert',
    author_email='eggertjannik@gmail.com',
    url='https://github.com/howprobable/py-helpers',
    install_requires=[
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
)