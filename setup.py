import distribute_setup
distribute_setup.use_setuptools()
from setuptools import setup

setup(
    name = "gipc",
    packages = ["gipc"],
    py_modules = ["distribute_setup"],
    version = "0.2.0",
    description = "gevent-cooperative multiprocessing and inter-process communication.",
    long_description=open("README").read().decode('utf-8'),
    author = "Jan-Philip Gehrcke",
    author_email = "jgehrcke@googlemail.com",
    url = "http://gehrcke.de/gipc",
    download_url = "http://gehrcke.de/gipc",
    keywords = ["gevent", "ipc", "multiprocessing"],
    license = "Apache License 2.0",
    platforms = ["POSIX", "Windows"],
    classifiers = [
        "Programming Language :: Python",
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: Apache Software License",
        "Intended Audience :: Developers",
        "Operating System :: POSIX",
        "Operating System :: Microsoft :: Windows",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Hardware :: Symmetric Multi-processing",
        ],
#    install_requires=("gevent>=1.0", "greenlet"),
)
