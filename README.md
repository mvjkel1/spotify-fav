# spotify-fav (for those who (really) don't like the Spotify "next song" algorithm)

## Current status

This project is currently in its early development stages, and the README is being actively updated. I will continue to refine and expand it as the project evolves.

### Overview

The project target is to serve as a personal tool to monitor Spotify listening habits.
It it capable to track the number of times you have listened to a track on Spotify.
Based on that it will be possible produce a playlist with the tracks you haven't skipped.

A song is considered not skipped / listened to the end if it is currently playing during polling and is about to finish (if there are 10 seconds or less remaining).

### Features (In progress)

- API with few endpoints, documented using Swagger.

### Technology stack

This project is being developed using Python and multiple libraries, the most important of which are:

FastAPI: responsible for the API endpoints.
SQLAlchemy: used to handle SQL queries.
httpx: serves as the HTTP client interface.
Alembic: used for database migrations in a more efficient way.
pytest: used for testing.

## Getting Started (In progress)

### Prerequisites (In progress)

### Installation (In progress)
