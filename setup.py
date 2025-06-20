import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

requirements = [
    'websockets>=14.0',
    'msgpack'
]

setuptools.setup(
    name="simpleobsws",
    version="1.4.3",
    author="tt2468",
    author_email="tt2468@gmail.com",
    description="A simple obs-websocket library in async Python for people who just want JSON output.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/IRLToolkit/simpleobsws",
    py_modules=['simpleobsws'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
        "Environment :: Plugins",
    ],
    python_requires='>=3.9',
    install_requires=requirements,
)
