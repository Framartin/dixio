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
    id_player2room = {}
    id_player2username = {}

    def on_error(e):
        app.logger.error('Error: {0}'.format(e))
        emit('error', {'message': 'An error has occurred: {0}'.format(e)})

    def on_connect(self):
        session['id_player'] = session.get('id_player', str(uuid4()))
        # create fake name if not already set
        lang = request.accept_languages.best_match(FAKER_LOCALES)
        session['username'] = session.get('username', Faker(lang).name())
        self.id_player2room[session['id_player']] = request.sid # TODO : do not support multiple room
        self.id_player2username[session['id_player']] = session['username']
        #emit('status', {'message': 'Waiting to join a game', 'status': 'lobby', 'action_needed': False})

    def on_join(self, message):
        # create game if don't exist
        if message['room'] not in self.games:
            if len(self.games) >= MAX_NB_GAMES:
                raise MaxNumberGamesError('Cannot create new game. The maximum number of games was reached. Try '
                                          'again later.')
            self.games[message['room']] = DixitGame()
        self.games[message['room']].add_player(session['id_player'])
        join_room(message['room'])

    def on_get_status(self, message):
        game = self.games.get(message['room'])
        status, message_status, action_needed = game.get_status_message_action(session.get('id_player'))
        emit('status',  {'message': message_status, 'status': status, 'action_needed': action_needed})

    def on_start_game(self, message):
        game = self.games.get(message['room'])
        game.start_game()
        emit('update_status', room=message['room'])
        emit('update_hand', room=message['room'])

    def on_get_hand(self, message):
        game = self.games.get(message['room'])
        emit('hand', {'ids_cards': game.get_hand(session.get('id_player'))})

    def on_tell(self, message):
        game = self.games.get(message['room'])
        game.tell(id_player=session.get('id_player'),
                  id_card=message['id_card'],
                  description=message['description'])
        emit('update_status', room=message['room'])
        emit('update_hand')

    def on_play(self, message):
        game = self.games.get(message['room'])
        game.tell(id_player=session.get('id_player'),
                  id_card=message['id_card'])
        emit('update_status', room=message['room'])  # TODO : only update everyone at status change to limit asynchrone issue
        emit('update_hand')

    def on_get_table(self, message):
        game = self.games.get(message['room'])
        emit('table', {'ids_cards': game.get_table(session.get('id_player'))})

    def on_vote(self, message):
        game = self.games.get(message['room'])
        game.vote(id_player=session.get('id_player'),
                  id_card=message['id_card'])
        emit('update_status', room=message['room'])  # TODO : only update everyone at status change to limit asynchrone issue

    # def on_leave(self, message):
    #     leave_room(message['room'])
    #     session['receive_count'] = session.get('receive_count', 0) + 1
    #     emit('my_response',
    #          {'data': 'In rooms: ' + ', '.join(rooms()),
    #           'count': session['receive_count']})

    # def on_close_room(self, message):
    #     session['receive_count'] = session.get('receive_count', 0) + 1
    #     emit('my_response', {'data': 'Room ' + message['room'] + ' is closing.',
    #                          'count': session['receive_count']},
    #          room=message['room'])
    #     close_room(message['room'])

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

    def on_disconnect(self):
        id_player = session.get('id_player')
        del self.id_player2room[id_player]
        # del self.id_player2username[id_player]  # TODO: have to keep id_player if reconnect


socketio.on_namespace(PlayNamespace('/play'))

if __name__ == '__main__':
    socketio.run(app, debug=DEBUG)
