from datetime import datetime
from os import mkdir, path
from re import match, search, sub
from sys import argv

from bs4 import BeautifulSoup as bs
from colorifix.colorifix import Color, Style, paint
from config import Config
from pymortafix.searching import HEADERS
from requests import get
from tabulate import tabulate


def sanitize(string):
    return sub("\n", "", string).strip()


def sanitize_song_name(name):
    return (m := search(r"^([^\(,\-\[\.]+)", name)) and m.group(1).strip()


def search_songs(query):
    Config.SPINNER.start(f"Searching for {paint(query,Color.BLUE)}")
    query = sub(r"\s+", "+", query)
    soup = bs(
        get(f"https://bsaber.com/?s={query}&orderby=relevance&order=DESC").text,
        "html.parser",
    )
    songs = [
        i for song in soup.findAll("div", {"class": "row"}) if (i := get_info(song))
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
    title = sanitize(row.find("header").text)
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
    return (title, difficulties, upvote, downvote, mapper, date, dwn_link)


def download_song(song_name, link, filename):
    colored_song_name = paint(song_name, Color.BLUE)
    if not link:
        Config.SPINNER.fail(f"No link working for {colored_song_name}")
    Config.SPINNER.start(f"Downloading {colored_song_name}")
    zip_song = get(link, headers=HEADERS)
    open(filename, "wb").write(zip_song.content)
    Config.SPINNER.succeed(f"Downloaded {colored_song_name}")


def get_spotify_songs(playlist_link):
    playlist = Config.SPOTIFY.playlist(playlist_link)
    return [
        (
            sanitize_song_name(song.get("track").get("name")),
            song.get("track").get("artists")[0].get("name"),
        )
        for song in playlist.get("tracks").get("items")
    ]


def retrieve_params(spotify=True):
    if spotify:
        spotify_playlist_link = input(
            paint("> ", Color.WHITE)
            + paint("Spotify", Color.GREEN)
            + paint(" playlist link: ", Color.WHITE)
        )
        while not search("https://open.spotify.com/playlist/", spotify_playlist_link):
            spotify_playlist_link = input(
                paint("Bad link!", Color.RED) + paint(" Retry: ", Color.WHITE)
            )
    playlist_name = input(paint("> Choose a name for the playlist: ", Color.WHITE))
    automatic = input(
        paint("> Do you want to choose for every songs? ", Color.WHITE)
        + paint("[y/n] ", Color.WHITE, style=Style.BOLD)
    ).lower() not in ("yes", "y", "")
    return spotify_playlist_link if spotify else None, automatic, playlist_name


def lines_splitting(name):
    MAX_CHAR = 45
    if len(name) <= MAX_CHAR:
        return paint(name, Color.WHITE)
    return paint(name[:MAX_CHAR], Color.WHITE) + "\n" + lines_splitting(name[MAX_CHAR:])


def songs_table(songs):
    headers = [
        paint(h, style=Style.BOLD)
        for h in ["", "Song", "Mapper", "Up", "Down", "Difficulty", "Date"]
    ]
    entries = [
        (
            i,
            lines_splitting(name),
            paint(mapper, Color.BLUE),
            paint(up, Color.GREEN),
            paint(down, Color.RED),
            paint(difficulties, Color.YELLOW),
            paint(f"{date:%d.%m.%Y}", Color.GRAY),
        )
        for i, (name, difficulties, up, down, mapper, date, _) in enumerate(songs, 1)
    ]
    return tabulate(entries, headers=headers, tablefmt="fancy_grid")


def combine_search(*songs_list):
    return list(set(sum(songs_list, start=[])))


def main():
    # from command line (file or single search)
    if len(argv) > 1:
        # search via file
        if search(r"\.\w+", argv[1]):
            try:
                songs_to_search = [
                    (lines, None) for lines in open(argv[1]).read().split("\n") if lines
                ]
            except FileNotFoundError:
                print(
                    paint("File ", Color.RED)
                    + paint(argv[1], Color.RED, style=Style.UNDERLINE)
                    + paint(" not found!", Color.RED)
                )
                exit(-1)
            print(
                paint("> Songs list provided via file ", Color.WHITE)
                + paint(argv[1], Color.BLUE)
            )
            _, automatic, playlist_name = retrieve_params(spotify=False)
        # search via text
        else:
            automatic = False
            playlist_name = None
            songs_to_search = [(argv[1], None)]
            print(
                paint("> Single song search ", Color.WHITE) + paint(argv[1], Color.BLUE)
            )
    # search via Spotify plalist
    else:
        spotify_playlist_link, automatic, playlist_name = retrieve_params()
        songs_to_search = [
            (f"{title} {artist}", title)
            for title, artist in get_spotify_songs(spotify_playlist_link)
        ]
    if playlist_name:
        if not path.exists(playlist_name):
            mkdir(playlist_name)
    print()
    # downloading
    for song_more, song_less in songs_to_search:
        bsaber_songs = search_songs(song_more)
        if song_less:
            bsaber_songs = combine_search(bsaber_songs, search_songs(song_less))
        if bsaber_songs:
            bsaber_songs = sorted(bsaber_songs, key=lambda x: -x[2] / (x[3] + 0.01))
            Config.SPINNER.succeed(f"Searched for {paint(song_more,Color.BLUE)}")
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
                selected_song = bsaber_songs[int(n) - 1]
                song_name, song_link = selected_song[0], selected_song[-1]
                filename = (
                    f"{playlist_name}/{song_name}.zip" if playlist_name else song_name
                )
                if not path.exists(filename):
                    download_song(song_name, song_link, filename)
                else:
                    Config.SPINNER.succeed(
                        f"Already downloaded {paint(song_more,Color.BLUE)}"
                    )
            else:
                Config.SPINNER.fail(f"Skipped {paint(song_more,Color.BLUE)}")
        else:
            Config.SPINNER.fail(f"No song found for {paint(song_more,Color.BLUE)}")
        print("\n")


if __name__ == "__main__":
    main()
