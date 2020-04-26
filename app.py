#!/usr/bin/env python
from threading import Lock
from flask import Flask, render_template, session, request
from flask_socketio import SocketIO, Namespace, emit, join_room, leave_room, \
    close_room, rooms, disconnect
from uuid import uuid4
from faker import Faker
from faker.config import AVAILABLE_LOCALES as FAKER_LOCALES
from game import DixitGame, NumberPlayersError

# REPLACE SECRET KEY AND SET DEBUG TO False BEFORE DEPLOYMENT
SECRET_KEY = "REPLACE_ME"
DEBUG = True
MAX_NB_GAMES = 1000
async_mode = "eventlet"

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
socketio = SocketIO(app, async_mode=async_mode)
thread = None
thread_lock = Lock()


class MaxNumberGamesError(Exception):
    pass


@app.route('/')
def index():
    return render_template('index.html', async_mode=socketio.async_mode)


class PlayNamespace(Namespace):
    games = {}

    def on_error(e):
        app.logger.error('Error: {0}'.format(e))
        emit('error', {'message': 'An error has occurred: {0}'.format(e)})

    def on_connect(self):
        session['id'] = session.get('id', str(uuid4()))
        # create fake name if not already set
        lang = request.accept_languages.best_match(FAKER_LOCALES)
        session['username'] = session.get('username', Faker(lang).name())
        emit('status', {'message': 'Waiting to join a game', 'action_needed': False})

    def on_join(self, message):
        # create game if don't exist
        if message['room'] not in self.games:
            if len(self.games) >= MAX_NB_GAMES:
                raise MaxNumberGamesError('Cannot create new game. The maximum number of games was reached. Try '
                                          'again later.')
            self.games[message['room']] = {
                'game': None,
                'players': [],
            }
        self.games[message['room']]['players'].append(session['id_player'])
        join_room(message['room'])

    def on_ask_status(self, message):
        game = self.games.get(message['room'])
        if game is None: (, 0, False)
        message, code, action_needed = \

        emit('status', )

    def on_create_game(self, message):
        try:
            self.games[message['room']]['game'] = DixitGame(ids_players=self.games[message['room']]['players'])
        except NumberPlayersError as e:
            emit('error', {'message': str(e)})
            return
        emit('status', {'message': 'Game starts! Wait for the first storyteller to play.'},
             room=message['room'])
        # TODO : emit to story teller with action_required
        # Send their cards to every player

    def on_tell(self, message):
        try:
            self.games[message['room']]['game'].tell(id_player=session.get('id'),
                                                     id_card=message['id_card'],
                                                     description=message['description'])
        except Exception as e:
            emit('error', {'message': str(e)})
            return
        emit('status', {
            'message': "{0} told a story. Choose your best card that describe".format(session.get('username'))
        },
             room=message['room'])
        # send action required

    def on_leave(self, message):
        leave_room(message['room'])
        session['receive_count'] = session.get('receive_count', 0) + 1
        emit('my_response',
             {'data': 'In rooms: ' + ', '.join(rooms()),
              'count': session['receive_count']})

    def on_close_room(self, message):
        session['receive_count'] = session.get('receive_count', 0) + 1
        emit('my_response', {'data': 'Room ' + message['room'] + ' is closing.',
                             'count': session['receive_count']},
             room=message['room'])
        close_room(message['room'])

    def on_my_room_event(self, message):
        session['receive_count'] = session.get('receive_count', 0) + 1
        emit('my_response',
             {'data': message['data'], 'count': session['receive_count']},
             room=message['room'])

    def on_disconnect_request(self):
        session['receive_count'] = session.get('receive_count', 0) + 1
        emit('my_response',
             {'data': 'Disconnected!', 'count': session['receive_count']})
        disconnect()

    def on_my_event(self, message):
        session['receive_count'] = session.get('receive_count', 0) + 1
        emit('my_response',
             {'data': message['data'], 'count': session['receive_count']})

    def on_my_broadcast_event(self, message):
        session['receive_count'] = session.get('receive_count', 0) + 1
        emit('my_response',
             {'data': message['data'], 'count': session['receive_count']},
             broadcast=True)

    def on_disconnect(self):
        print('Client disconnected', request.sid)


socketio.on_namespace(PlayNamespace('/play'))

if __name__ == '__main__':
    socketio.run(app, debug=DEBUG)
