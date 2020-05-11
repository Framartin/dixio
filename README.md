# DixIO

KISS implementation of famous board game Dixit in Python with Flask-SocketIO

> Created with love and care during the COVID-19 pandemic to be able to play with family and friends 😷💌🏩

## Features

- **KISS**: no account, no lobby, no password. Just share your game link to your friends
- Support multiple games from same browser
- No database, no flat-file, the current games are loaded on RAM.

## Limitations

- Not possible to change browser during a game

## Set up you own server

### Installation

- Install Python3.7+.
- Create a virtual environment
```
python3 -m venv venv
. venv/bin/activate
pip install -r requirements.txt
```
- Configure the server:
    - Set a strong `SECRET_KEY`, for example by running `python -c 'import os; print(os.urandom(16))'`
    - Make sure that `DEBUG` is set to `False`
- You may need the [Deployment section](https://flask-socketio.readthedocs.io/en/latest/#deployment) of the Flask-SocketIO documentation

### Run the server

```
. venv/bin/activate
python app.py
```