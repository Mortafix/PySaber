import json
import re
import unicodedata
import urllib.request
from argparse import ArgumentParser
from os import mkdir, path
from re import match, search

import requests
from halo import Halo
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOauthError
from tabulate import tabulate

SPINNER = Halo()


# Config


def get_config() -> dict:
    return json.load(open(f"{path.abspath(path.dirname(__file__))}/config.json", "r"))


def save_config(client_id: str, secret_id: str) -> None:
    keys = {"spotify-id": client_id, "spotify-secret-id": secret_id}
    json.dump(
        keys, open(f"{path.abspath(path.dirname(__file__))}/config.json", "w"), indent=4
    )


def sanitize_song_name(name: str) -> str:
    return (m := search(r"^([^(,\-\[.]+)", name)) and m.group(1).strip()


def slugify(value: str, allow_unicode=False) -> str:
    """
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value)
    return re.sub(r'[-\s]+', '-', value).strip('-_')


def download_song(song_name: str, link: str, filename: str) -> None:
    colored_song_name = song_name
    if not link:
        SPINNER.fail(f"No link working for {colored_song_name}")
    SPINNER.start(f"Downloading {colored_song_name}")
    urllib.request.urlretrieve(link, filename)
    SPINNER.succeed(f"Downloaded {colored_song_name}")


def get_spotify_songs(playlist_link: str) -> list[tuple]:
    playlist = {}
    try:
        authConfig = get_config()
        client = Spotify(
            auth_manager=SpotifyClientCredentials(
                client_id=authConfig["spotify-id"], client_secret=authConfig["spotify-secret-id"]
            )
        )
        # TODO: Work on offsets.
        playlist.update(client.playlist_items(playlist_link, offset=0))
    except SpotifyOauthError:
        print("\n" + "Error! " + "Please run the configuration once.")
        print("Run " + "saberio --config")
        exit(-1)

    return [
        (
            sanitize_song_name(song.get("track").get("name")),
            song.get("track").get("artists")[0].get("name"),
        )
        for song in playlist.get("items")
    ]


def retrieve_params(args) -> tuple:
    spotify_playlist_link = None
    if not args.file and not args.song:
        spotify_playlist_link = input(
            "> "
            + "Spotify"
            + " playlist link: "
        )
        while not search("https://open.spotify.com/playlist/", spotify_playlist_link):
            spotify_playlist_link = input(
                "Bad link!" + " Retry: "
            )
    if not args.p:
        playlist_name = input("> Choose a name for the playlist: ")
    else:
        playlist_name = args.p
    if not args.auto and not args.list and not args.test:
        while (
                automatic := input(
                    "> Choose mode: "
                    + "[auto|list|test] "
                ).lower()
        ) not in ("auto", "list", "test"):
            pass
        auto = automatic != "list"
        test = automatic == "test"
    else:
        auto = not args.list
        test = args.test

    return spotify_playlist_link, playlist_name, auto, test


def lines_splitting(name):
    MAX_CHAR = 45
    if len(name) <= MAX_CHAR:
        return name
    return name[:MAX_CHAR] + "\n" + lines_splitting(name[MAX_CHAR:])


def songs_table(songs):
    headers = [
        h
        for h in ["", "Code", "Song", "Mapper", "Up", "Down", "Duration"]  # , "Date"]
    ]
    entries = [
        (
            i,
            currentSong["id"],
            lines_splitting(currentSong["name"]),
            currentSong["uploader"]["name"],
            currentSong["stats"]["upvotes"],
            currentSong["stats"]["downvotes"],
            currentSong["metadata"]["duration"],
            # f"{updatedAt:%d.%m.%Y}",
        )
        for i, currentSong in enumerate(songs)
    ]
    return tabulate(
        entries, headers=headers, tablefmt="fancy_grid", disable_numparse=True
    )


def special_song_name(lines):
    if (m := search(r"(.*?)(#\w+)?\s*$", lines)) and m.group(2):
        return m.group(2)[1:], m.group(1).strip()
    else:
        return None, lines


def argparsing():
    parser = ArgumentParser(
        prog="PySaber",
        description="Let's rock on Beat Saber.",
        usage=(
            "pysaber [-f file] [--auto|--no-auto|--auto-test] [-p playlist-name] "
            "[--path path-to-playlist]"
        ),
        epilog="Example: pysaber -f songs.txt -p BeastSaver --no-auto",
    )
    parser.add_argument(
        "-s", "--song", type=str, help="song name for a single search", metavar="FILE"
    )
    parser.add_argument(
        "-f", "--file", type=str, help="text file with a songs list", metavar="SONG"
    )
    parser.add_argument("-p", type=str, help="playlist name", metavar="PLAYLIST")
    parser.add_argument(
        "-d",
        "--dir",
        type=str,
        help="path where to save the songs (playlist parent folder)",
        metavar="PATH",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--auto",
        action="store_true",
        help="automatic download first matching song",
    )
    group.add_argument(
        "--list",
        action="store_true",
        help="choose a song from the matching list for every songs",
    )
    group.add_argument(
        "--test",
        action="store_true",
        help="test automatic matching withuout downloading",
    )
    parser.add_argument(
        "--config",
        help="Spotify configuration",
        action="store_true",
    )
    parser.add_argument(
        "-v",
        "--version",
        help="script version",
        action="version",
        version="pysaber v0.2.1",
    )
    return parser.parse_args()


def main():
    args = argparsing()

    # spotify config
    if args.config:
        print("To get a key, go to https://developer.spotify.com/dashboard/applications and create a new application.")
        client_id = input("Client ID: ")
        secret_id = input("Secret ID: ")
        save_config(client_id, secret_id)
        try:
            client = Spotify(
                client_credentials_manager=SpotifyClientCredentials(
                    client_id, secret_id
                )
            )
            client.search("test")
            print("Configuration successful!")
        except SpotifyOauthError:
            print("Configuration failed.")
        exit(-1)

    # script
    if args.dir and not path.exists(path.join(args.dir)):
        print(
            "Path "
            + args.dir
            + " doesn't exist!"
        )
        exit(-1)
    path_to_folder = args.dir or "."
    spotify_playlist_link, playlist_name, automatic, test = retrieve_params(args=args)

    songs_to_search = []
    if args.file:
        try:
            songs_to_search = [
                (*special_song_name(lines), None)
                for lines in open(args.file).read().split("\n")
                if lines
            ]
        except FileNotFoundError:
            print(
                "File "
                + args.file
                + " not found!"
            )
            exit(-1)
        print(
            "> Songs list provided via file "
            + args.file
        )
    elif args.song:
        songs_to_search = [(*special_song_name(args.song), None)]
        print(
            "> Single song search " + args.song
        )
    else:
        songs_to_search = [
            (None, f"{title} {artist}", title)
            for title, artist in get_spotify_songs(spotify_playlist_link)
        ]
        print(
            "> Songs list provided via "
            + "Spotify playlist"
        )
    if not test and not path.exists(path.join(path_to_folder, playlist_name)):
        mkdir(path.join(path_to_folder, playlist_name))

    # downloading
    for code_song, song_more, song_less in songs_to_search:
        song_to_download = None
        if not code_song:
            bsaber_songs = requests.get(
                "https://beatsaver.com/api/search/text/0",
                params={"sortOrder": "Relevance", "q": song_more}
            ).json()["docs"]
            SPINNER.succeed(f"Searched for {song_more}")
            if len(bsaber_songs) > 0:
                if not automatic:
                    print(songs_table(bsaber_songs))
                    n = input("> Choose a song: [0:skip] ")
                    while not match(r"\d+", n) or int(n) not in range(
                            len(bsaber_songs) + 1
                    ):
                        n = input(
                            "Wrong!  "
                            + "> Retry: [0:skip] "
                        )
                else:
                    n = 1
                if int(n):
                    song_to_download = bsaber_songs[int(n) - 1]
                else:
                    SPINNER.fail(f"Skipped {song_more}")
            else:
                SPINNER.fail(f"No song found for {song_more}")
        else:
            SPINNER.succeed(
                f"Searched for {song_more} "
                f"[{code_song}]"
            )

        # song downloading
        if song_to_download:
            code_song = song_to_download["id"]
            song_name = song_to_download["name"]
            song_link = song_to_download["versions"][-1]["downloadURL"]
            path_to_file = path.join(
                path_to_folder,
                playlist_name,
                slugify(song_name)
            )
            filename = f"{path_to_file}.zip" if playlist_name else song_name
            if test:
                SPINNER.succeed(f"Matched with {song_name}")
            elif not path.exists(filename):
                download_song(song_name, song_link, filename)
            else:
                SPINNER.succeed(f"Already downloaded {song_name}")
            open(path.join(path_to_folder, f"{playlist_name}.log"), "a+").write(
                f"{song_name} #{code_song}\n"
            )
        print("\n")


if __name__ == "__main__":
    main()
