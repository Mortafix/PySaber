from datetime import datetime
from re import search, sub

from bs4 import BeautifulSoup as bs
from colorifix.colorifix import paint
from halo import Halo
from requests import get
from tabulate import tabulate

SPINNER = Halo()
MAX_CHAR = 45

# ---- Utils


def lines_splitting(name):
    if len(name) <= MAX_CHAR:
        return paint(f"[#white]{name}[/]")
    return paint(f"[#white]{name[:MAX_CHAR]}[/]\n{lines_splitting(name[MAX_CHAR:])}")


def songs_table(songs):
    fields = ["", "Code", "Song", "Mapper", "Up", "Down", "Difficulty", "Date"]
    headers = [paint(f"[@bold]{field}[/]") for field in fields]
    entries = [
        (
            i,
            paint(f"[#magenta]{code}[/]"),
            lines_splitting(name),
            paint(f"[#blue]{mapper}[/]"),
            paint(f"[#green]{up}[/]"),
            paint(f"[#red]{down}[/]"),
            paint(f"[#yellow]{diff}[/]"),
            paint(f"[#gray]{date:%d.%m.%Y}[/]"),
        )
        for i, (code, name, _, diff, up, down, mapper, date) in enumerate(songs, 1)
    ]
    return tabulate(entries, headers=headers, tablefmt="fancy_grid")


def look_for_code(song):
    if (m := search(r"(.*?)(\#\w+)?\s*$", song or "")) and m.group(2):
        return m.group(2)[1:], m.group(1).strip()
    return None, song


# ---- Songs


def search_songs(query):
    SPINNER.start(paint(f"Searching for [#blue]{query}[/]"))
    query = sub(r"\s+", "+", query)
    url = f"https://bsaber.com/?s={query}&orderby=relevance&order=DESC"
    songs_html = bs(get(url).text, "html.parser").findAll("div", {"class": "row"})
    return [info for song in songs_html if (info := get_info(song))]


def get_info(song):
    if song.find("div", {"class": ["widget", "small-2", "subfooter-menu-holder"]}):
        return None
    header = song.find("header")
    sanitize = lambda string: sub("\n", "", string).strip()
    code = (m := search(r"songs/(\w+)/", header.find("a").get("href"))) and m.group(1)
    title = sanitize(header.text)
    difficulties_html = song.findAll("a", {"class": "post-difficulty"})
    trunc_difficulty = lambda df: df == "Expert+" and "Ex+" or df[:2]
    difficulties = ", ".join(trunc_difficulty(df.text) for df in difficulties_html)
    stats_html = song.findAll("span", {"class": "post-stat"})[1:]
    stats = [int(sanitize(s.text)) for s in stats_html]
    upvote, downvote = stats or (0, 0)
    mapper_html = song.find("div", {"class": "post-bottom-meta post-mapper-id-meta"})
    mapper = search(r"\n+(\w+)", mapper_html.text or "").group(1)
    date = datetime.fromisoformat(song.find("time").get("content"))
    dwn_link = (link := song.find("a", {"class": "-download-zip"})) and link.get("href")
    return code, title, dwn_link, difficulties, upvote, downvote, mapper, date


def get_info_by_code(code):
    soup = bs(get(f"https://bsaber.com/songs/{code}").text, "html.parser")
    header = soup.find("header", {"class": "post-title"})
    name = header.find("h1").text
    link = f"https://beatsaver.com/api/download/key/{code}"
    return code, name, link


def download_song(song_name, link, filename):
    if not link:
        SPINNER.fail(paint(f"No link working for [#blue]{song_name}[/]"))
    SPINNER.start(paint(f"Downloading [#blue]{song_name}[/]"))
    zip_song = get(link)
    open(filename, "wb").write(zip_song.content)
    SPINNER.succeed(paint(f"Downloaded [#blue]{song_name}[/]"))
