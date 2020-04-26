from random import shuffle
from itertools import cycle
from collections import Counter
from datetime import datetime

NB_CARDS = 84


class GameEndedError(Exception):
    pass


class NumberPlayersError(ValueError):
    pass


class ActionImpossibleNow(Exception):
    pass


class NotReadyToVoteError(ActionImpossibleNow):
    pass


class DixitGame:

    def __init__(self):
        self.datetime_start = datetime.utcnow()
        self.points = Counter()
        self.status = 'lobby'
        self.ids_players = []
        self.pile = list(range(1, NB_CARDS + 1))
        self.past_turns = []
        self.hands = self.ids_players_turn_generator = self.current_turn = None

    def get_status_message_action(self, id_player):
        self._sanity_check(id_player=id_player)
        action_needed = False
        status = self.status
        # not all players have joined
        if status == 'lobby':
            message = 'You\'re in the game. Wait for other players and start the game if everyone is ready'
        # wait for the storyteller to provide card & description
        elif status == 'tell':
            if id_player == self.current_turn['id_player_storyteller']:
                message = 'Choose 1 card in your hand and enter a short description. The description can be a single ' \
                          'word, multiple words, an entire sentence, a quote, a extract of a song, etc. It should not ' \
                          'be too simple (e.g. "A shell on the beach") nor too hard.'
                action_needed = True
            else:
                message = 'Wait for the storyteller to choose a card and its description.'
        # wait for other players to play a card
        elif status == 'play':
            if id_player == self.current_turn['id_player_storyteller']:
                message = 'Wait for other players to to choose a card corresponding to your description.'
            else:
                if id_player not in self.current_turn['table']:
                    message = 'Choose a card among your hand that correspond best with the storyteller\'s description.'
                    action_needed = True
                else:
                    nb_missing_cards = len(self.ids_players)-len(self.current_turn['table'])
                    message = 'Wait for other players to play a card ({0} missing).'.format(nb_missing_cards)
        # wait for other players to vote
        elif status == 'vote':
            if id_player == self.current_turn['id_player_storyteller']:
                message = 'Wait for other players to vote for a card on the table.'
            else:
                if id_player not in self.current_turn['votes']:
                    message = 'Vote for 1 card on the table that you think is the one of the storyteller.'
                    action_needed = True
                else:
                    nb_missing_cards = len(self.ids_players)-len(self.current_turn['votes'])-1
                    message = 'Wait for other players to vote ({0} missing).'.format(nb_missing_cards)
        # give some time for players to see results of this turn, before starting a new one
        elif status == 'end_turn':
            message = 'See the results of this turn. Next turn incoming.'
        elif status == 'end_game':
            message = 'Game ended!'
        else NotImplementedError('Error with game status: {0}'.format(status))
        return status, message, action_needed

    def add_player(self, id_player):
        if self.status != 'lobby':
            raise ActionImpossibleNow('You cannot join. The game has already started.')
        if id_player not in self.ids_players:
            self.ids_players.append(id_player)

    def start_game(self):
        if len(self.ids_players) not in [4, 5, 6]:
            raise NumberPlayersError("There must be between 4 and 6 players.")
        shuffle(self.ids_players)
        shuffle(self.pile)
        self.hands = {x: [] for x in ids_players}
        self.ids_players_turn_generator = cycle(ids_players)
        self.current_turn = {
            'id_player_storyteller': next(self.ids_players_turn_generator),
            'table': {},
            'description': None,
            'votes': {},
        }
        for _ in range(0, 6):
            self._distribute()
        self.status = 'tell'

    def _distribute(self):
        """
        Distribute one card to each player
        """
        if len(self.pile) < len(self.ids_players):
            raise GameEndedError("Game ended")
        for id_player in self.ids_players:
            id_card = self.pile.pop()
            self.hands[id_player].append(id_card)

    def _sanity_check(self, id_player, id_card=None):
        if id_player not in self.ids_players:
            raise ValueError('Player not in game')
        if id_card is not None:
            if id_card not in self.hands[id_player]:
                raise ValueError("Card not in player's hand")

    def get_hand(self, id_player):
        self._sanity_check(id_player=id_player)
        return self.hands[id_player]

    def tell(self, id_player, id_card, description):
        self._sanity_check(id_player=id_player, id_card=id_card)
        if self.status != 'tell':
            raise ActionImpossibleNow("Impossible to tell at this stage")
        if id_player != self.current_turn['id_player_storyteller']:
            raise ValueError("Only the storyteller can vote")
        self.hands[id_player].remove(id_card)
        self.current_turn['id_player_storyteller'] = id_player
        self.current_turn['description'] = description
        self.current_turn['table'][id_player] = id_card
        self.status = 'play'

    def play(self, id_player, id_card):
        """
        Other players choose a card to place on the table
        :param id_player:
        :param id_card:
        :return: True if all players have played
        """
        self._sanity_check(id_player=id_player, id_card=id_card)
        if self.status != 'play':
            raise ActionImpossibleNow("Impossible to play a card at this stage")
        if id_player == self.current_turn['id_player_storyteller']:
            raise ValueError("The storyteller cannot play")
        self.hands[id_player].remove(id_card)
        self.current_turn['table'][id_player] = id_card
        if len(current_turn['table']) == len(self.ids_players):
            self.status = 'vote'

    def get_table(self):
        if len(self.current_turn['table']) != len(self.ids_players):
            raise NotReadyToVoteError("Election not ready")
        table_ids_cards = self.current_turn['table'].values()
        shuffle(table_ids_cards)
        return table_ids_cards

    def vote(self, id_player, id_card):
        """
        Other players vote for one of the card on the table
        :param id_player:
        :param id_card:
        :return: True if all other players have cast their vote
        """
        self._sanity_check(id_player=id_player, id_card=id_card)
        if id_player == self.current_turn['id_player_storyteller']:
            raise ValueError("The storyteller cannot vote")
        if id_card == self.current_turn["table"][id_player]:
            raise ValueError("You cannot vote for your own card")
        self.current_turn['table'][id_player] = id_card
        if len(self.current_turn['vote']) == len(self.ids_players) - 1:
            self._update_points_with_current_turn()
            self.status = 'end_turn'

    def _update_points_with_current_turn(self):
        if len(current_turn['table']) != len(self.ids_players):
            raise ValueError("Some cards missing")
        if len(self.current_turn['vote']) != len(self.ids_players) - 1:
            raise ValueError("Not all players has voted")
        points_current_turn = Counter()
        id_player_storyteller = self.current_turn['id_player_storyteller']
        # list of players except storyteller
        ids_players_others = self.ids_players.copy()
        ids_players_others.remove(id_player_storyteller)
        # if all players voted for the same card (ie. all or nobody for the storyteller's one)
        if len(set(self.current_turn['vote'].values())) == 1:
            for id_player in ids_players_others:
                points_current_turn[id_player] += 2
        else:
            points_current_turn[id_player_storyteller] += 3
            for id_player in ids_players_others:
                # 3 points for others players who correctly guessed
                if self.current_turn['vote'][id_player] == self.current_turn['table'][id_player_storyteller]:
                    points_current_turn[id_player] += 3
                # if wrong vote, add 1 point for the card owner
                else:
                    # extract card owner
                    id_player_owner_list = [k for k, v in self.current_turn['table'].items() if
                                            v == self.current_turn['vote'][id_player]]
                    if len(id_player_owner_list) != 1:
                        raise RuntimeError("Could not extract who place the card")
                    points_current_turn[id_player_owner_list[0]] += 1
        self.points += points_current_turn
        self.current_turn['points'] = points_current_turn

    def end_turn(self):
        # save current turn
        self.past_turns.append(self.current_turn)
        try:
            self._distribute()
        except GameEndedError:
            self.status = 'end_game'
            return
        # set next storytellers
        self.current_turn = {
            'id_player_storyteller': next(self.ids_players_turn_generator),
            'table': {},
            'description': None,
            'votes': {},
        }
        # distribute new cards
        self.status = 'tell'

    def get_points_table_vote_last_turn(self):
        last_turn = self.past_turns[-1]
        return last_turn['points'], last_turn['table'], last_turn['vote']

    def get_stats(self):
        return {
            'points': self.points,
        }