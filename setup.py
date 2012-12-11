from distutils.core import setup

setup(
    name = "gipc",
    packages = ["gipc"],
    version = "0.1.0",
    description = "Multiprocessing and IPC for gevent",
    long_description=open("README").read().decode('utf-8'),
    author = "Jan-Philip Gehrcke",
    author_email = "jgehrcke@googlemail.com",
    url = "http://gehrcke.de/gipc",
    download_url = "http://gehrcke.de/gipc",
    keywords = ["gevent", "ipc", "multiprocessing"],
    classifiers = [
        "Programming Language :: Python",
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: Apache Software License",
        "Intended Audience :: Developers",
        #"Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX",
        "Operating System :: Microsoft :: Windows",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Hardware :: Symmetric Multi-processing",
        ],
    install_requires=("gevent", "greenlet"),
)
