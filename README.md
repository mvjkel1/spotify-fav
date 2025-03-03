# spotify-fav

_(For those who (really) don't like the Spotify "next song" algorithm)_

## Overview

**spotify-fav** is a personal tool designed to track your listening habits on Spotify. It monitors how often you've played a track and helps you create playlists based on songs you haven't skipped. A song is considered "not skipped" if it's still playing with 10 seconds or less remaining when the system polls the current playback state.
Since the API is not deployed anywhere (it runs on localhost), it is needed to follow all the steps mentioned in "Getting Started" section below.

### Prerequisites

- Python 3.12+
- Spotify Developer Account (for API credentials)

## Features

- RESTful API with few endpoints documented using Swagger/OpenAPI. Its mainly features are:
  - Tracking the number of times a song is fully listened to.
  - Generating playlists based on your listening behavior (tracks you haven't skipped).

## Technology Stack

This project leverages the following key technologies:

- **FastAPI**: For building API endpoints.
- **SQLAlchemy**: To interact with the database using SQL.
- **httpx**: HTTP client used for communicating with Spotify's API.
- **Alembic**: For managing database migrations efficiently.
- **pytest**: For writing and running unit and integration tests.

## Getting Started

- Clone the repository
- Create and activate the Python virtual environment
- Install all packages mentioned in requirements.txt by running `pip install -r <path_to_requirements.txt>`
- Modify the .env_example file (stored in spotify-fav/src/server) to match your Spotify API and DB credentials

```
NOTE:

I have been using the Postgres DB platform provided by the https://neon.tech/
```

- Rename the .env_example to .env
- Run alembic migrations
  - Run the `alembic init alembic` command inside ./spotify-fav/src/server directory to initialize alembic migrations
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
- To access the core API routes, you need to log in first, to do it:
  - Generate the Login URL: Execute the /user-auth/login route to generate your unique login URL
  - Authenticate: Copy the URL and paste it into your browser. Enter your Spotify credentials to log in
  - After successful login you should be redirected back to `http://127.0.0.1:8000/docs`
- Have fun
