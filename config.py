from halo import Halo
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials


class Config:
    SPINNER = Halo()
    _SPOTIFY_ID = "client-id"
    _SPOTIFY_SECRET_ID = "secret-id"
    SPOTIFY = Spotify(
        client_credentials_manager=SpotifyClientCredentials(
            _SPOTIFY_ID, _SPOTIFY_SECRET_ID
        )
    )
