import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="saberio",
    version="1.0.1",
    author="Moris Doratiotto",
    author_email="moris.doratiotto@gmail.com",
    description="A python module to download song for Beat Saber",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mortafix/PySaber",
    packages=setuptools.find_packages(),
    install_requires=[
        "beautifulsoup4 == 4.11.1",
        "colorifix == 2.0.4",
        "pymortafix == 0.2.2",
        "halo == 0.0.31",
        "tabulate == 0.8.10",
        "wcwidth == 0.2.6",
        "spotipy== 2.22.1",
    ],
    classifiers=[
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
    ],
    python_requires=">=3.9",
    keywords=["beat saber", "bsaber", "beat saver"],
    package_data={"pysaber": ["utils/helpers.py"]},
    entry_points={"console_scripts": ["saberio=pysaber.saberio:main"]},
)
