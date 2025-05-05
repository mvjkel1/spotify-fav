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
However, if you’d like to use the API before its official release, it works perfectly on localhost. See the guide below for setup instructions.

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

### Prerequisites

- Python 3.12+
- Spotify Developer Account (for API credentials)
- PostgresSQL database
- Redis database

## Getting Started

- Clone the repository
- Create and activate the Python virtual environment
- Install all packages mentioned in requirements.txt by running

`pip install -r <path_to_requirements.txt>`

- Modify the .env_example file (stored in spotify-fav/src/server) to match your Spotify API and DB credentials

> [!IMPORTANT]
> 
> I have been using the PostgresDB platform provided by the https://neon.tech/.
> The Redis database that I have used is running on https://upstash.com/.

- Rename the .env_example to .env
- Run alembic migrations
  - Run the `alembic init alembic` command inside `./spotify-fav/src/server` directory to initialize alembic migrations
  - Modify the alembic.ini configuration file - provide the sqlalchemy.url
  - Modify the env.py file inside the alembic directory

```python
from app.db.models import Base
.
.
# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata
```

- Run the migrations:

  - `alembic revision --autogenerate -m "<your_msg>"`
  - `alembic upgrade heads`

- Execute the `run.sh` script, e.g. `./run.sh server`
- Open the browser and navigate to `http://127.0.0.1:8000/docs`
- To access the core API routes, you need to register first, to do so:
  - Execute the /user-auth/register route to make an account, (the e-mail is not relevant at the moment, so you could use anything you like as long it is in the e-mail form)
  - Look for the [🔒] padlock icon in the Swagger UI to authorize API requests
  - Execute the /spotify-auth/login route to generate your unique Spotify login URL
  - Authenticate Spotify - copy the URL and paste it into your browser. Enter your Spotify credentials to log in
  - After successful login you should be redirected back to `http://127.0.0.1:8000/docs`
- Have fun
