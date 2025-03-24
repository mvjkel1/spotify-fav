# spotify-fav  
*(For those who (really) don't like the Spotify "next song" algorithm)*

## Project Status

**Early Development**  
This project is still in its early stages, and the README will be expanded as features are added and refined.

## Overview

**spotify-fav** is a personal tool designed to track your listening habits on Spotify. It monitors how often you've played a track and helps you create playlists based on songs you haven't skipped. A song is considered "not skipped" if it's still playing with 10 seconds or less remaining when the system polls the current playback state.

## Features (In Progress)

- RESTful API with endpoints documented using Swagger/OpenAPI.
- Tracks the number of times a song is fully listened to.
- Playlist generation based on your listening behavior (tracks you haven't skipped).

## Technology Stack

This project leverages the following key technologies:

- **FastAPI**: For building API endpoints.
- **SQLAlchemy**: To interact with the database using SQL.
- **httpx**: HTTP client used for communicating with Spotify's API.
- **Alembic**: For managing database migrations efficiently.
- **pytest**: For writing and running unit and integration tests.

## Getting Started (In Progress)

### Prerequisites

- Python 3.x
- Spotify Developer Account (for API credentials)

### Installation

*Instructions to be added soon.*
