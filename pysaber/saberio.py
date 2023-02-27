from argparse import ArgumentParser
from os import makedirs, path

from colorifix.colorifix import paint, ppaint
from pymortafix.utils import multisub, strict_input
from pysaber.utils.helpers import (SPINNER, download_song, get_info_by_code,
                                   look_for_code, search_songs, songs_table,
                                   bookmark_song)
from pysaber.utils.spotify import(retrieve_params, get_spotify_songs)


def argparsing():
    parser = ArgumentParser(
        prog="PySaber",
        description="Let's rock on Beat Saber.",
        usage=("pysaber [-f file] [-s song] [--auto|--list|--test] [-p playlist-name]"),
        epilog="Example: pysaber -f songs.txt -p BeastSaver --list",
    )
    parser.add_argument("-p", type=str, help="playlist name", metavar=("PLAYLIST"))
    parser.add_argument(
        "-d",
        "--dir",
        type=str,
        help="path where to save the songs (playlist parent folder)",
        metavar=("PATH"),
    )
    search = parser.add_mutually_exclusive_group()
    search.add_argument(
        "-s", "--song", type=str, help="song name for a single search", metavar=("FILE")
    )
    search.add_argument(
        "-f", "--file", type=str, help="text file with a songs list", metavar=("SONG")
    )
    bookmark = parser.add_argument_group()
    bookmark.add_argument(
        "-c", "--cookie", type=str, help="cookie for bookmarking."
    )
    bookmark.add_argument(
        '-b', action="store_true", help="bookmark all songs searched from BeastSaber."
    )
    bookmark.add_argument(
        "-o", action="store_true", help="bookmark songs without downloading."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--auto",
        action="store_true",
        help="automatic download first matching song",
    )
    mode.add_argument(
        "--list",
        action="store_true",
        help="choose a song from the matching list for every songs",
    )
    mode.add_argument(
        "--test",
        action="store_true",
        help="test automatic matching withuout downloading",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="log every run of the script",
    )
    return parser.parse_args()


def main():
    args = argparsing()
    spotify_playlist_link, playlist_name = retrieve_params(args)

    # default
    path_to_folder = args.dir and path.dirname(path.join((args.dir or "."), playlist_name)) or '.'
    playlist_name = args.p or "songs"
    automatic = not args.list or args.auto or args.test
    is_test = args.test or False
    mode_name = (is_test and "test") or (automatic and "auto") or "list"
        
    # check
    if args.dir and not path.exists(path.join(args.dir)):
        ppaint(f"[#red]Path [@underline]{args.dir}[/@] doesn't exist![/]")
        exit(-1)
    if args.file and not path.exists(path.join(args.file)):
        ppaint(f"[#red]File [@underline]{args.file}[/@] doesn't exist![/]")
        exit(-1)

    # param: songs
    songs = list()
    if args.file:
        songs = [
            look_for_code(line) for line in open(args.file).read().split("\n") if line
        ]
        ppaint(f"> Songs list file: [#gray @bold]{args.file}[/]")
    elif args.song:
        songs = [look_for_code(args.song)]
        ppaint(f"> Search: [#gray @bold]{args.song}[/]")
    elif spotify_playlist_link != None: 
        songs = [(None, f"{track} {artist}") for track, artist in get_spotify_songs(spotify_playlist_link)]


    ppaint(
        f"> Folder: [#gray @bold]{path_to_folder}[/]\n"
        f"> Playlist: [#gray @bold]{playlist_name}[/]\n"
        f"> Mode: [#gray @bold]{mode_name}[/]"
    )

    if not is_test and not args.o and not path.exists(path.join(path_to_folder, playlist_name)):
        makedirs(path.join(path_to_folder, playlist_name))
    print()

    # searching
    for code_song, song_more in songs:
        song_to_download = None
        if not code_song:
            bsaber_songs = search_songs(song_more)
            SPINNER.succeed(paint(f"Search complete for [#blue]{song_more}[/]"))
            if bsaber_songs:
                bsaber_songs = sorted(
                    bsaber_songs, key=lambda x: (-x[5] + 1) / (x[6] + 1)
                )
                n = 1
                if not automatic:
                    print(songs_table(bsaber_songs))
                    n = strict_input(
                        paint("> Choose a song: [@underline][0:skip][/] "),
                        choices=list(map(str, range(len(bsaber_songs) + 1))),
                        flush=True
                    )
                if int(n) > 0:
                    song_to_download = bsaber_songs[int(n) - 1]
                    if args.cookie and (args.b or strict_input(
                                paint('> Whether to add to the bookmark? [Y/n]'),
                                choices=['y', 'n', 'Y', 'N', ''],
                                flush=True) in ('y', 'Y', '')): 
                        bookmark_song(song_to_download[3], song_to_download[1], args.cookie)
                        if args.o: continue
                else:
                    SPINNER.fail(paint(f"Skipped [#blue]{song_more}[/]"))
            else:
                SPINNER.fail(paint(f"No song found for [#blue]{song_more}[/]"))
        else:
            msg = f"Song [#blue]{song_more}[/] with code [#magenta]{code_song}[/] found"
            SPINNER.succeed(paint(msg))
            song_to_download = get_info_by_code(code_song)

        # downloading
        if song_to_download:
            code_song, song_name, song_link = song_to_download[:3]
            sanitezed_name = multisub({"/": "_", " – ": "_", " ": "_"}, song_name)
            path_to_file = path.join(path_to_folder, playlist_name, sanitezed_name)
            filename = f"{path_to_file}.zip"
            if is_test:
                SPINNER.succeed(paint(f"Matched with [#blue]{song_name}[/]"))
            elif path.exists(filename):
                SPINNER.succeed(paint(f"Already downloaded [#blue]{song_name}[/]"))
            else:
                download_song(song_name, song_link, filename)
            # log
            if args.verbose:
                log_file = path.join(path_to_folder, f"{playlist_name}.log")
                open(log_file, "a+").write(f"{song_name} #{code_song}\n")
        print()


if __name__ == "__main__":
    main()
