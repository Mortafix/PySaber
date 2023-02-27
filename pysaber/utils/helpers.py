from datetime import datetime
from re import search, sub

from bs4 import BeautifulSoup as bs
from colorifix.colorifix import paint
from halo import Halo
from requests import get, post
from tabulate import tabulate

SPINNER = Halo()

# ---- Utils


def songs_table(songs):
    fields = ["", "Code", "Song", "Mapper", "Up", "Down", "Difficulty", "Date"]
    headers = [paint(f"[@bold]{field}[/]") for field in fields]
    entries = [
        (
            i,
            paint(f"[#magenta]{code}[/]"),
            paint(name),
            paint(f"[#blue]{mapper}[/]"),
            paint(f"[#green]{up}[/]"),
            paint(f"[#red]{down}[/]"),
            paint(f"[#yellow]{diff}[/]"),
            paint(f"[#gray]{date:%d.%m.%Y}[/]"),
        )
        for i, (code, name, _, _, diff, up, down, mapper, date) in enumerate(songs, 1)
    ]
    return tabulate(entries, headers=headers, tablefmt="fancy_grid", maxcolwidths=[None, None, 45])


def look_for_code(song):
    if (m := search(r"(.*?)(\#\w+)?\s*$", song or "")) and m.group(2):
        return m.group(2)[1:], m.group(1).strip()
    return None, song


# ---- Songs


def search_songs(query):
    SPINNER.start(paint(f"Searching for [#blue]{query}[/]"))
    query = sub(r"\s+", "+", query)
    url = f"https://bsaber.com/?s={query}&orderby=relevance&order=DESC"
    songs_html = bs(get(url).text, "html.parser").find_all("div", {"class": "row"})
    return [info for song in songs_html if (info := get_info(song))]

def get_info(song):
    if not song.header:
        return None
    if song.find("div", {"class": ["widget", "small-2", "subfooter-menu-holder"]}):
        return None
    sanitize = lambda string: sub("\n", "", string).strip()
    code = song.header.a.get("href").split('/')[-2]
    title = sanitize(song.header.text)
    difficulties_html = song.find_all("a", {"class": "post-difficulty"})
    trunc_difficulty = lambda df: df == "Expert+" and "Ex+" or df[:2]
    difficulties = ", ".join(trunc_difficulty(df.text) for df in difficulties_html)
    upvote = int(song.find("i", class_="fa fa-thumbs-up fa-fw").next_sibling)
    downvote = int(song.find("i", class_="fa fa-thumbs-down fa-fw").next_sibling)
    mapper_html = song.find("div", {"class": "post-bottom-meta post-mapper-id-meta"})
    mapper = search(r"\n+(\w+)", mapper_html.text or "").group(1)
    date = datetime.fromisoformat(song.find("time").get("content"))
    dwn_link = (link := song.find("a", {"class": "-download-zip"})) and link.get("href")
    bookmark_id = (id := song.find("a", {"class": "-bookmark"})) and id.get("data-id")
    return code, title, dwn_link, bookmark_id, difficulties, upvote, downvote, mapper, date

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

def bookmark_song(id, song_name, cookie):
    if '200' in (ret := str(post("https://bsaber.com/wp-admin/admin-ajax.php", 
        headers={
        "Host": "bsaber.com",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/110.0",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://bsaber.com/?s=halo&orderby=relevance&order=DESC",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Length": "61",
        "Origin": "https://bsaber.com",
        "Connection": "keep-alive",
        "Cookie": cookie,
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Site": "same-origin",
    },  data={"action": "bsaber_bookmark_post",
             "type": "add_bookmark",
             "post_id": id,
             }))): SPINNER.succeed(paint(f"Bookmarked [#blue]{song_name}[/]"))
    else: SPINNER.fail(paint(f"Bookmark failed [#blue]{id}[/] [#yellow]{song_name}[/] [#red]{ret.strip('<Response []>')}[/]"))