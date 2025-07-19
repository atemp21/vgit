from setuptools import setup, find_packages

setup(
    name="vgit",
    version="0.1.0",
    packages=find_packages(include=["app", "app.*"]),
    install_requires=[
        "click>=8.2.1,<9.0.0",
        "gitpython>=3.1.44,<4.0.0",
    ],
    entry_points={
        "console_scripts": [
            "vgit=app.cli:main",
            "vg=app.cli:main",
        ],
    },
    python_requires=">=3.12",
)
