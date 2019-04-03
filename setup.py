from setuptools import setup, find_packages

install_requires = [
    "pyqt5",
    "requests",
    "sqlalchemy==1.3.1",
]

setup(
    name="torrent_automator",
    version="0.1",
    description="Automate Searching and Downloading Torrents",
    author="bwallad",
    author_email="bwallad@gmail.com",
    install_requires=install_requires,
    scripts=[],
    packages=find_packages(),
    python_requires=">=3.6",
)
