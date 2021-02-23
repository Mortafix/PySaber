from argparse import ArgumentParser
from datetime import datetime
from json import dump, load
from os import mkdir, path
from re import match, search, sub

from bs4 import BeautifulSoup as bs
from colorifix.colorifix import Color, Style, paint
from halo import Halo
from pymortafix.searching import HEADERS
from requests import get
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOauthError
from tabulate import tabulate

SPINNER = Halo()

# Config


def get_config():
    return load(open(f"{path.abspath(path.dirname(__file__))}/config.json", "r"))


def save_config(client_id, secret_id):
    keys = {"spotify-id": client_id, "spotify-secret-id": secret_id}
    dump(
        keys, open(f"{path.abspath(path.dirname(__file__))}/config.json", "w"), indent=4
    )


# Utilities


def sanitize(string):
    return sub("\n", "", string).strip()


def sanitize_song_name(name):
    return (m := search(r"^([^\(,\-\[\.]+)", name)) and m.group(1).strip()


def search_songs(query):
    SPINNER.start(f"Searching for {paint(query,Color.BLUE)}")
    query = sub(r"\s+", "+", query)
    soup = bs(
        get(f"https://bsaber.com/?s={query}&orderby=relevance&order=DESC").text,
        "html.parser",
    )
    songs = [
        i
        for song in soup.findAll("div", {"class": "row"})
        if (i := get_info(song)) and i[0]
    ]
    return songs


def trunc_difficulty(difficulty):
    diff = {
        "Easy": "Ea",
        "Normal": "No",
        "Hard": "Ha",
        "Expert": "Ex",
        "Expert+": "Ex+",
        "Standard": "St",
        "Advanced": "Ad",
    }
    return diff.get(difficulty) or difficulty


def get_info(row):
    if row.find("div", {"class": ["widget", "small-2", "subfooter-menu-holder"]}):
        return None
    header = row.find("header")
    code = (m := search(r"songs/(\w+)/", header.find("a").get("href"))) and m.group(1)
    title = sanitize(header.text)
    difficulties = ", ".join(
        [
            trunc_difficulty(d.text)
            for d in row.findAll("a", {"class": "post-difficulty"})
        ]
    )
    stats = [
        int(sanitize(s.text)) for s in row.findAll("span", {"class": "post-stat"})[1:]
    ]
    upvote, downvote = stats if stats else (0, 0)
    mapper = search(
        r"\n+(\w+)",
        (m := row.find("div", {"class": "post-bottom-meta post-mapper-id-meta"}))
        and m.text
        or "",
    ).group(1)
    date = datetime.fromisoformat(row.find("time").get("content"))
    dwn_link = (link := row.find("a", {"class": "-download-zip"})) and link.get("href")
    return (code, title, dwn_link, difficulties, upvote, downvote, mapper, date)


def get_info_by_code(code):
    soup = bs(get(f"https://bsaber.com/songs/{code}").text, "html.parser")
    header = soup.find("header", {"class": "post-title"})
    name = header.find("h1").text
    link = f"https://beatsaver.com/api/download/key/{code}"
    return code, name, link


def download_song(song_name, link, filename):
    colored_song_name = paint(song_name, Color.BLUE)
    if not link:
        SPINNER.fail(f"No link working for {colored_song_name}")
    SPINNER.start(f"Downloading {colored_song_name}")
    zip_song = get(link, headers=HEADERS)
    open(filename, "wb").write(zip_song.content)
    SPINNER.succeed(f"Downloaded {colored_song_name}")


def get_spotify_songs(playlist_link):
    config = get_config()
    try:
        client = Spotify(
            client_credentials_manager=SpotifyClientCredentials(
                config.get("spotify-id"), config.get("spotify-secret-id")
            )
        )
        playlist = client.playlist(playlist_link)
    except SpotifyOauthError:
        print("\n" + paint("Error! ", Color.RED) + "Please run the configuration once.")
        print("Run " + paint("saberio --config", Color.BLUE))
        exit(-1)
    return [
        (
            sanitize_song_name(song.get("track").get("name")),
            song.get("track").get("artists")[0].get("name"),
        )
        for song in playlist.get("tracks").get("items")
    ]


def retrieve_params(args):
    spotify_playlist_link = None
    if not args.file and not args.song:
        spotify_playlist_link = input(
            paint("> ", Color.WHITE)
            + paint("Spotify", Color.GREEN)
            + paint(" playlist link: ", Color.WHITE)
        )
        while not search("https://open.spotify.com/playlist/", spotify_playlist_link):
            spotify_playlist_link = input(
                paint("Bad link!", Color.RED) + paint(" Retry: ", Color.WHITE)
            )
    if not args.p:
        playlist_name = input(paint("> Choose a name for the playlist: ", Color.WHITE))
    else:
        playlist_name = args.p
    if not args.auto and not args.list and not args.test:
        while (
            automatic := input(
                paint("> Choose mode: ", Color.WHITE)
                + paint("[auto|list|test] ", Color.WHITE, style=Style.BOLD)
            ).lower()
        ) not in ("auto", "list", "test"):
            pass
        auto = automatic != "list"
        test = automatic == "test"
    else:
        auto = not args.list
        test = args.test
    return (spotify_playlist_link, playlist_name, auto, test)


def lines_splitting(name):
    MAX_CHAR = 45
    if len(name) <= MAX_CHAR:
        return paint(name, Color.WHITE)
    return paint(name[:MAX_CHAR], Color.WHITE) + "\n" + lines_splitting(name[MAX_CHAR:])


def songs_table(songs):
    headers = [
        paint(h, style=Style.BOLD)
        for h in ["", "Code", "Song", "Mapper", "Up", "Down", "Difficulty", "Date"]
    ]
    entries = [
        (
            i,
            paint(code, Color.MAGENTA),
            lines_splitting(name),
            paint(mapper, Color.BLUE),
            paint(up, Color.GREEN),
            paint(down, Color.RED),
            paint(difficulties, Color.YELLOW),
            paint(f"{date:%d.%m.%Y}", Color.GRAY),
        )
        for i, (code, name, _, difficulties, up, down, mapper, date) in enumerate(
            songs, 1
        )
    ]
    return tabulate(
        entries, headers=headers, tablefmt="fancy_grid", disable_numparse=True
    )


def combine_search(*songs_list):
    return list(set(sum(songs_list, start=[])))


def special_song_name(lines):
    if (m := search(r"(.*?)(\#\w+)?\s*$", lines)) and m.group(2):
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
        "-s", "--song", type=str, help="song name for a single search", metavar=("FILE")
    )
    parser.add_argument(
        "-f", "--file", type=str, help="text file with a songs list", metavar=("SONG")
    )
    parser.add_argument("-p", type=str, help="playlist name", metavar=("PLAYLIST"))
    parser.add_argument(
        "-d",
        "--dir",
        type=str,
        help="path where to save the songs (playlist parent folder)",
        metavar=("PATH"),
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
        version="pysaber v0.2.0",
    )
    return parser.parse_args()


def main():
    args = argparsing()

    # spotify config
    if args.config:
        print(
            "To get a key, go to "
            + paint(
                "https://developer.spotify.com/dashboard/applications", Color.MAGENTA
            )
            + " and create a new application."
        )
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
            print(paint("Configuration successful!", Color.GREEN))
        except SpotifyOauthError:
            print(paint("Configuration failed.", Color.RED))
        exit(-1)

    # script
    if args.dir and not path.exists(path.join(args.dir)):
        print(
            paint("Path ", Color.RED)
            + paint(args.dir, Color.RED, style=Style.UNDERLINE)
            + paint(" doesn't exist!", Color.RED)
        )
        exit(-1)
    path_to_folder = args.dir or "."
    spotify_playlist_link, playlist_name, automatic, test = retrieve_params(args=args)
    if args.file:
        try:
            songs_to_search = [
                (*special_song_name(lines), None)
                for lines in open(args.file).read().split("\n")
                if lines
            ]
        except FileNotFoundError:
            print(
                paint("File ", Color.RED)
                + paint(args.file, Color.RED, style=Style.UNDERLINE)
                + paint(" not found!", Color.RED)
            )
            exit(-1)
        print(
            paint("> Songs list provided via file ", Color.WHITE)
            + paint(args.file, Color.BLUE)
        )
    elif args.song:
        songs_to_search = [(*special_song_name(args.song), None)]
        print(
            paint("> Single song search ", Color.WHITE) + paint(args.song, Color.BLUE)
        )
    else:
        songs_to_search = [
            (None, f"{title} {artist}", title)
            for title, artist in get_spotify_songs(spotify_playlist_link)
        ]
        print(
            paint("> Songs list provided via ", Color.WHITE)
            + paint("Spotify playlist", Color.BLUE)
        )
    if not test and not path.exists(path.join(path_to_folder, playlist_name)):
        mkdir(path.join(path_to_folder, playlist_name))
    print()
    # downloading
    for code_song, song_more, song_less in songs_to_search:
        song_to_download = None
        if not code_song:
            bsaber_songs = search_songs(song_more)
            if song_less:
                bsaber_songs = combine_search(bsaber_songs, search_songs(song_less))
            SPINNER.succeed(f"Searched for {paint(song_more,Color.BLUE)}")
            if bsaber_songs:
                bsaber_songs = sorted(
                    bsaber_songs, key=lambda x: (-x[4] + 1) / (x[5] + 1)
                )
                if not automatic:
                    print(songs_table(bsaber_songs))
                    n = input(paint("> Choose a song: [0:skip] ", Color.WHITE))
                    while not match(r"\d+", n) or int(n) not in range(
                        len(bsaber_songs) + 1
                    ):
                        n = input(
                            paint("Wrong!  ", Color.RED)
                            + paint("> Retry: [0:skip] ", Color.WHITE)
                        )
                else:
                    n = 1
                if int(n):
                    song_to_download = bsaber_songs[int(n) - 1]
                else:
                    SPINNER.fail(f"Skipped {paint(song_more,Color.BLUE)}")
            else:
                SPINNER.fail(f"No song found for {paint(song_more,Color.BLUE)}")
        else:
            SPINNER.succeed(
                f"Searched for {paint(song_more,Color.BLUE)} "
                f"[{paint(code_song,Color.MAGENTA)}]"
            )
            song_to_download = get_info_by_code(code_song)
        # song downloading
        if song_to_download:
            code_song, song_name, song_link = song_to_download[:3]
            path_to_file = path.join(path_to_folder, playlist_name, song_name)
            filename = f"{path_to_file}.zip" if playlist_name else song_name
            if test:
                SPINNER.succeed(f"Matched with {paint(song_name,Color.BLUE)}")
            elif not path.exists(filename):
                download_song(song_name, song_link, filename)
            else:
                SPINNER.succeed(f"Already downloaded {paint(song_name,Color.BLUE)}")
            open(path.join(path_to_folder, f"{playlist_name}.log"), "a+").write(
                f"{song_name} #{code_song}\n"
            )
        print("\n")


if __name__ == "__main__":
    main()
