![PyPI - Python Version](https://img.shields.io/pypi/pyversions/saberio)
[![PyPI](https://img.shields.io/pypi/v/nepox?color=red)](https://pypi.org/project/saberio/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
![GitHub](https://img.shields.io/github/license/mortafix/pysaber)

# Setup
You can find the package, [here](https://pypi.org/project/saberio/).
```
pip3 install saberio
```

# Usage
You can use the help (`-h`) for more information.
```bash
saberio # simple with Spotify
saberio -p PlaylistWow --auto -f path/to/file/songs-wow.txt
```

# Parameters
There are some parameters you can combine to customize the downloading process.

* The package can be use with a **Spotify playlist**, a **text file** or a **single song**.
```bash
# Spotify required no parameters, link will be asked later
saberio
> Spotify playlist link:

# text file must be specified via parameter
saberio -f path/to/file/myfile.txt

# single song must be specified via parameter
saberio -s "Alone - Alan Walker"
```

* The package can be runned in 3 mode: **auto**, **list** or **test**. If you don't specify the parameter, mode will be asked later.
```bash
# download the first matching song
saberio --auto

# provide a list with the best matching songs
saberio --list

# test the auto mode without downloading all the songs
saberio --test
```

* The package will ask you for the **playlist name**, and it can be provided via parameter. If you don't specify it, it will be asked later.
```bash
saberio -p MyPlaylist
```

* You can specify the **path** where to download all the song with an optional parameter.
```bash
saberio -d /path/to/playlist
```