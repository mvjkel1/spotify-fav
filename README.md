# spotify-fav

_For those who (really) don't like the Spotify "next song" algorithm_

## Overview

**_spotify-fav_** is an API designed to track your listening habits on Spotify.

It is capable of monitoring how often you've played a certain track on Spotify and help you create playlists based on songs you haven't skipped. A song is considered `played` if it has been listened to for at least 10 seconds and `not skipped` if it's still playing with 10 seconds or less remaining when the system polls the current playback state.

[CURRENTLY OFF] Its "demo" version is already deployed at [CURRENTLY OFF]:

https://spotify-fav-production.up.railway.app/docs

> [!IMPORTANT]
>
> At the current state, the API is deployed in the `Development mode`, so it wouldn't work for everyone.
Spotify allows me to add certain users which could use the API until I ask them for a review to make it official (accessible for everyone).
At the moment I am working on expanding its functionality, documenting and testing it as thoroughly as possible.

## Features

- RESTful API with few endpoints documented using Swagger. Its mainly features are:
  - Tracking the number of times a song is fully listened to
  - Generating playlists based on your listening behavior (tracks you haven't skipped)
  - Displaying Spotify personal data (tracks, playlists, etc.)

## Technology Stack

This project leverages the following key technologies:

- **FastAPI**: For building API endpoints
- **SQLAlchemy**: To interact with the database
- **httpx**: For communicating with Spotify's API
- **Alembic**: For managing database migrations efficiently
- **pytest**: For writing and running unit and integration tests
- **Redis**: For caching purposes
- **Prometheus**: For collecting and exposing metrics
- **Docker**: For containerizing the application

