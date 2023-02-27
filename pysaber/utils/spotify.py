from re import search
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOauthError
from colorifix.colorifix import paint
from pymortafix.utils import strict_input
from json import dump, load
from os import path
from halo import Halo
SPINNER = Halo()


# spotify config
def create_config():
    paint("To get a key, go to [#magenta]https://developer.spotify.com/dashboard/applications[/] and create a new application.")
    client_id = input("Client ID: ")
    secret_id = input("Secret ID: ")
    save_config(client_id=client_id, secret_id=secret_id)
    try:
        while True:
            try:
                client = Spotify(
                    client_credentials_manager=SpotifyClientCredentials(
                        client_id, secret_id
                    )
                )
                client.search("test")
                SPINNER.succeed("Configuration successful!")
                raise StopIteration
            except SpotifyOauthError:
                SPINNER.fail("Configuration failed.")
                create_config()
    except StopIteration:
        pass

def get_config():
    while True:
        try: 
            m = load(open(f"{path.abspath(path.dirname(__file__))}/config.json", "r"))
            return m
        except FileNotFoundError: create_config()


def save_config(**kargs):
    f = f"{path.abspath(path.dirname(__file__))}/config.json"
    keys = kargs
    if path.exists(f): keys = get_config() | kargs
    dump(
        keys, open(f, "w"), indent=4
    )


def sanitize_song_name(name):
    return (m := search(r"^([^\(,\-\[\.]+)", name)) and m.group(1).strip()


def get_spotify_songs(playlist_link):
    config = get_config()
    while not search("https://open.spotify.com/playlist/", playlist_link):
        playlist_link = input(
            paint("[#red]Bad link![/] [#white]Retry[/]: ")
        )
    while True:
        try:
            client = Spotify(
                client_credentials_manager=SpotifyClientCredentials(
                    config.get("client_id"), config.get("secret_id")
                )
            )
            playlist = client.playlist(playlist_link)
            break
        except SpotifyOauthError:
            SPINNER.fail(paint("[#red]Error![/] Please update the configuration once."))
            create_config()
    return [
        (
            sanitize_song_name(song.get("track").get("name")), # Track
            song.get("track").get("artists")[0].get("name"),   # Artist
        )
        for song in playlist.get("tracks").get("items")
    ]


def retrieve_params(args):
    spotify_playlist_link = None
    if not args.file and not args.song:
        if (m := input(paint("[#cyan]Type[/] the song or the playlist path right here. [#cyan]Or Press[/] [#green]ENTER[/] to enter spotify playlist link. ❯ "))) == '':
            spotify_playlist_link = input(
                paint("> [#green]Spotify[/] playlist link: ")
            )
        elif path.exists(m): args.file = m
        else: args.song = m
    if not (args.auto and args.list and args.test and args.c):
        while (
            choice := input(
                paint("> Choose mode: [[#red]auto[/]|[#green]list[/]|[#magenta]test[/][#yellow]|[/][#red][auto][/] [#blue]bookmark[/] [#cyan][and download][/]]. ❯ ")
            ).lower()
        ) not in ("auto", "list", "test") + (b := ("bookmark", "auto bookmark", 
                                                   "bookmark and download", 
                                                   "auto bookmark and download")):
            pass
        if choice in b and not args.cookie:
            if type(get_config().get("cookie")) != str: 
                args.cookie = strict_input(paint("Cookie from [#blue]B[/]saber.com\n ❯ "), wrong_text='', flush= True)
                save_config(cookie=args.cookie)
            else:
                args.cookie = get_config()['cookie']
        args.auto = args.b = (choice == "auto" 
                     or choice == "auto bookmark" 
                     or choice == "auto bookmark and download" 
                     or choice == "test")
        args.test = choice == "test"
        args.list = (choice == "list" or choice == "bookmark" or choice == "bookmark and download")
        args.o = (choice == "bookmark" or choice == "auto bookmark")
    if not args.p and not args.test and not args.o:
        playlist_name = args.p = input(paint("> Choose a name for the playlist. (songs)❯ "))
    else: playlist_name = args.p
    return spotify_playlist_link, playlist_name