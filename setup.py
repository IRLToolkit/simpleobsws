import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

requirements = open('requirements.txt', 'rt').readlines()

setuptools.setup(
    name="simpleobsws",
    version="0.0.7",
    author="tt2468",
    author_email="tt2468@gmail.com",
    description="A simple obs-websocket library in async Python for people who just want JSON output.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/IRLToolkit/simpleobsws",
    py_modules=['simpleobsws'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
        "Environment :: Plugins",
    ],
    python_requires='>=3.6',
    install_requires=requirements,
)
