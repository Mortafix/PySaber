import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="saberio",
    version="0.2.0",
    author="Moris Doratiotto",
    author_email="moris.doratiotto@gmail.com",
    description="A python module to download song for Beat Saber",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mortafix/PySaber",
    packages=setuptools.find_packages(),
    install_requires=["bs4", "pymortafix", "halo", "spotipy", "tabulate"],
    classifiers=[
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
    ],
    python_requires=">=3.8",
    keywords=["beat saber", "spotify", "bsaber", "beat saver"],
    package_data={"pysaber": ["config.json"]},
    entry_points={"console_scripts": ["saberio=pysaber.saberio:main"]},
)
