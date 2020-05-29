#!/usr/bin/env python
from threading import Lock
from flask import Flask, render_template, session, request
from flask_socketio import SocketIO, Namespace, emit, join_room, leave_room, \
    close_room, rooms, disconnect
from uuid import uuid4
from faker import Faker
from faker.config import AVAILABLE_LOCALES as FAKER_LOCALES
from random import sample
from datetime import datetime, timedelta
from game import DixitGame

# REPLACE SECRET KEY AND SET DEBUG TO False BEFORE DEPLOYMENT
SECRET_KEY = "REPLACE_ME"
DEBUG = False
MAX_NB_GAMES = 500
MAX_NB_GAMES_CHECK = 50
MAX_MINUTES_GAME_TIME = 6*60
async_mode = "eventlet"

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
socketio = SocketIO(app, async_mode=async_mode)


class MaxNumberGamesError(Exception):
    pass


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/game/<game_name>')
def game_route(game_name):
    # set player's session, if not already set
    session['id_player'] = session.get('id_player', str(uuid4()))
    # create fake name if not already set
    lang = request.accept_languages.best_match(FAKER_LOCALES)
    session['username'] = session.get('username', Faker(lang).name())
    return render_template('game.html', game_name=game_name, username=session['username'])


@socketio.on_error(namespace='/play')
def play_error_handler(e):
    app.logger.error('Error: {0}'.format(e))
    emit('notification_error', {'message': 'Error: {0}'.format(e)})
    if DEBUG:
        raise e


class PlayNamespace(Namespace):
    games = {}
    #id_player2room = {}
    id_player2username = {}

    def on_connect(self):
        #self.id_player2room[session['id_player']] = request.sid  # TODO : do not support multiple room
        self.id_player2username[session['id_player']] = session['username']

    def on_join(self, message):
        # create game if don't exist
        if message['room'] not in self.games:
            # clean old room
            sample_game_name = sample(self.games.keys(), min(len(self.games), MAX_NB_GAMES_CHECK))  # sample a list
            # of maximum MAX_NB_GAMES_CHECK games
            for game_name in sample_game_name:
                if (datetime.utcnow() - self.games[game_name].datetime_start) > timedelta(minutes=MAX_MINUTES_GAME_TIME):
                    self.games.pop(game_name)
            # check if possible to create new one
            if len(self.games) >= MAX_NB_GAMES:
                raise MaxNumberGamesError('Cannot create new game. The maximum number of games was reached. Try '
                                          'again later.')
            self.games[message['room']] = DixitGame(debug=DEBUG)
        game = self.games.get(message['room'])
        game.add_player(session['id_player'])
        join_room(message['room'])
        # send status
        status, message_status, action_needed, description = game.get_status_message_action_description(
            session.get('id_player'))
        emit('status',
             {
                 'message': message_status,
                 'status': status,
                 'action_needed': action_needed,
                 'description': description,
                 'on_join': True,
             })

    def on_get_status(self, message):
        game = self.games.get(message['room'])
        status, message_status, action_needed, description = game.get_status_message_action_description(
            session.get('id_player'))
        emit('status',
             {
                 'message': message_status,
                 'status': status,
                 'action_needed': action_needed,
                 'description': description,
                 'on_join': False,
             })

    def on_start_game(self, message):
        game = self.games.get(message['room'])
        game.start_game()
        emit('update_status', room=message['room'])
        emit('update_hand', room=message['room'])
        emit('update_points', room=message['room'])

    def on_get_hand(self, message):
        game = self.games.get(message['room'])
        emit('hand', {'ids_cards': game.get_hand(session.get('id_player'))})

    def on_tell(self, message):
        game = self.games.get(message['room'])
        game.tell(id_player=session.get('id_player'),
                  id_card=message['id_card'],
                  description=message['description'])
        emit('update_hand')
        emit('update_status', room=message['room'])

    def on_play(self, message):
        game = self.games.get(message['room'])
        game.play(id_player=session.get('id_player'),
                  id_card=message['id_card'])
        emit('update_hand')
        # update everyone status to update message that contains number of players remaining
        emit('update_status', room=message['room'])
        # update table if status has changed
        if game.status != 'play':
            emit('update_table', room=message['room'])

    def on_get_table(self, message):
        game = self.games.get(message['room'])
        emit('table', {'ids_cards': game.get_table()})

    def on_vote(self, message):
        game = self.games.get(message['room'])
        game.vote(id_player=session.get('id_player'),
                  id_card=message['id_card'])
        # if turn ended on that vote, start new turn, add new card in hand, clear table
        if game.status == 'end_turn':
            game.end_turn()
            emit('update_table', room=message['room'])
            emit('update_last_turn', room=message['room'])
            emit('update_hand', room=message['room'])
            emit('update_points', room=message['room'])
        emit('update_status', room=message['room'])

    def on_get_last_turn(self, message):
        game = self.games.get(message['room'])
        last_turn_dict = game.get_last_turn()  # points, table, votes
        if last_turn_dict is None:
            return
        id_player = session.get('id_player')
        last_turn = []
        for k, v in last_turn_dict['table'].items():  # TODO
            # k: id_player, v: id_card
            last_turn.append({
                'username': self.id_player2username[k],
                'id_card': v,
                'points': last_turn_dict['points'][k],
                'usernames_voters': [self.id_player2username[k2] for k2, v2 in last_turn_dict['votes'].items() if
                                     v2 == v],
                'highlight': k == id_player,  # highlight if current player # TODO : support it in HTML
            })
        emit('last_turn', {'last_turn': last_turn})

    def on_get_points(self, message):
        game = self.games.get(message['room'])
        points_dict = game.points
        id_player = session.get('id_player')
        table_points = []
        for k, v in points_dict.items():
            # k: id_player, v: nb of points
            table_points.append({
                'username': self.id_player2username[k],
                'points': v,
                'highlight': k == id_player,  # highlight if current player
            })
        emit('points', {'points': table_points})

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

    # def on_my_room_event(self, message):
    #     session['receive_count'] = session.get('receive_count', 0) + 1
    #     emit('my_response',
    #          {'data': message['data'], 'count': session['receive_count']},
    #          room=message['room'])

    # def on_disconnect_request(self):
    #     session['receive_count'] = session.get('receive_count', 0) + 1
    #     emit('my_response',
    #          {'data': 'Disconnected!', 'count': session['receive_count']})
    #     disconnect()

    def on_disconnect(self):
        id_player = session.get('id_player')
        # TODO remove player for game if in lobby
        #del self.id_player2room[id_player]
        # del self.id_player2username[id_player]  # TODO: have to keep id_player if reconnect
        # TODO: delete game if nobody is left on the party?


socketio.on_namespace(PlayNamespace('/play'))

if __name__ == '__main__':
    socketio.run(app, debug=DEBUG)
