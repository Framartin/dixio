# OpenDixit

KISS implementation of famous board game Dixit in Python with Flask-SocketIO

## Features

- **KISS**: no account, no lobby, no password. Just share a link to your friends. 
- Support multiple games from same browser

## Limitations

- It's impossible to change browser during a game

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
    
### Run the server

```
. venv/bin/activate
python app.py
```