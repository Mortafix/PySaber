from datetime import datetime
from re import search, sub
from sys import argv

from bs4 import BeautifulSoup as bs
from colorifix.colorifix import Color, Style, paint
from halo import Halo
from pymortafix.searching import HEADERS
from requests import get

SPINNER = Halo()


def sanitize(string):
    return sub("\n", "", string).strip()


def search_songs(query):
    SPINNER.start(f"Searching for {paint(query,Color.BLUE)}")
    query = sub(r"\s+", "+", query)
    soup = bs(
        get(f"https://bsaber.com/?s={query}&orderby=relevance&order=DESC").text,
        "html.parser",
    )
    songs = [
        i for song in soup.findAll("div", {"class": "row"}) if (i := get_info(song))
    ]
    SPINNER.clear()
    return songs


def get_info(row):
    if row.find("div", {"class": ["widget", "small-2", "subfooter-menu-holder"]}):
        return None
    title = sanitize(row.find("header").text)
    difficulties = [d.text for d in row.findAll("a", {"class": "post-difficulty"})]
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
    dwn_link = (l := row.find("a", {"class": "-download-zip"})) and l.get("href")
    return (title, difficulties, upvote, downvote, mapper, date, dwn_link)


def download_song(song_name, link):
    colored_song_name = paint(song_name, Color.BLUE)
    if not link:
        SPINNER.fail(f"No link working for {colored_song_name}")
    SPINNER.start(f"Downloading {colored_song_name}")
    zip_song = get(link, headers=HEADERS)
    open(f"{song_name}.zip", "wb").write(zip_song.content)
    SPINNER.succeed(f"Downloaded {colored_song_name}")


def get_spotify_songs(playlist):
    soup = bs(get(playlist).text, "html.parser")
    titles = [s.text for s in soup.findAll("span", {"class": "track-name"})]
    artits = [
        s.find("a").text for s in soup.findAll("span", {"class": "artists-albums"})
    ]
    return list(zip(titles, artits))


if __name__ == "__main__":
    playlist = "https://open.spotify.com/playlist/2fkvaAkmkzpZwxd79toEJx"
    if len(argv) < 2:
        print(paint("ERROR! You need to specify the song(s) name.", Color.RED))
        print(
            paint("USAGE", Color.GRAY),
            paint("python3 script.py song-name", style=Style.UNDERLINE),
        )
        exit(-1)
    # TODO: argparse for text file or Spotify playlist
    # songs_to_search = [lines for lines in open(argv[1]).read().split("\n") if lines]
    songs_to_search = [f"{title}" for title, artist in get_spotify_songs(playlist)]
    # TODO: search only for title if title+artist fail
    for song in songs_to_search:
        songs = search_songs(song)
        if not songs:
            SPINNER.fail(f"No song found for {paint(song,Color.BLUE)}")
        else:
            selected_song = songs[0]
            download_song(selected_song[0], selected_song[-1])
