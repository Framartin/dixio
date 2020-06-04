from random import shuffle
from itertools import cycle
from collections import Counter, OrderedDict
from datetime import datetime

NB_CARDS = 84


class GameException(Exception):
    pass


class PlayerError(GameException):
    pass


class CardError(GameException):
    pass


class GameEndedError(GameException):
    pass


class NumberPlayersError(GameException):
    pass


class ActionImpossibleNow(GameException):
    pass


class DescriptionError(GameException):
    pass


class DixioGame:

    def __init__(self, debug=False):
        self.datetime_start = datetime.utcnow()
        self._points = Counter()
        self.status = 'lobby'
        self.ids_players = []
        self.pile = list(range(1, NB_CARDS + 1))
        self.past_turns = []
        self.hands = self.ids_players_turn_generator = self.current_turn = None
        self.debug = debug

    def _sanity_check(self, id_player, id_card=None):
        if id_player not in self.ids_players:
            raise PlayerError('Player not in game')
        if id_card is not None:
            if id_card not in self.hands[id_player]:
                raise CardError("Card not in player's hand")

    def _distribute(self):
        """
        Distribute one card to each player
        """
        if len(self.pile) < len(self.ids_players):
            raise GameEndedError("Game ended")
        for id_player in self.ids_players:
            id_card = self.pile.pop()
            self.hands[id_player].append(id_card)

    def get_status_dict(self, id_player, on_join=False):
        self._sanity_check(id_player=id_player)
        action_needed = False
        status = self.status
        description = None
        if self.current_turn is not None:
            description = self.current_turn['description']
        # not all players have joined
        if status == 'lobby':
            message = f'You\'re in the game. Wait for other players and start the game when everyone is ready.<br>'\
                      f'{len(self.ids_players)} player(s) currently in game.'
        # wait for the storyteller to provide card & description
        elif status == 'tell':
            if id_player == self.current_turn['id_player_storyteller']:
                message = 'Enter a short description corresponding to one card in your hand. Then click this card ' \
                          'to validate your play.'
                action_needed = True
            else:
                message = 'Wait for the storyteller to choose a card and its description.'
        # wait for other players to play a card
        elif status == 'play':
            nb_missing_cards = len(self.ids_players) - len(self.current_turn['table'])
            if id_player == self.current_turn['id_player_storyteller']:
                message = f'Wait for other players to to choose a card corresponding to your description ' \
                          f'({nb_missing_cards} missing).'
            else:
                if id_player not in self.current_turn['table']:
                    message = 'Choose a card among your hand that best corresponds to the storyteller\'s description.'
                    action_needed = True
                else:
                    message = f'Wait for other players to play a card ({nb_missing_cards} missing).'
        # wait for other players to vote
        elif status == 'vote':
            nb_missing_cards = len(self.ids_players) - len(self.current_turn['votes']) - 1
            if id_player == self.current_turn['id_player_storyteller']:
                message = f'Wait for other players to vote for a card on the table ({nb_missing_cards} missing).'
            else:
                if id_player not in self.current_turn['votes']:
                    message = 'Vote for 1 card on the table that you think is the one of the storyteller.'
                    action_needed = True
                else:
                    message = f'Wait for other players to vote ({nb_missing_cards} missing).'
        # give some time for players to see results of this turn, before starting a new one
        elif status == 'end_turn':
            message = 'See the results of this turn. Next turn incoming.'
        elif status == 'end_game':
            message = 'Game ended! Results are below.'
        else:
            raise NotImplementedError('Error with game status: {0}'.format(status))
        return {
                 'message': message,
                 'status': status,
                 'action_needed': action_needed,
                 'description': description,
                 'on_join': on_join,
                 'nb_cards_pile': len(self.pile),
             }

    def add_player(self, id_player):
        if id_player in self.ids_players:
            return
        if self.status != 'lobby':
            raise ActionImpossibleNow('You cannot join. The game has already started.')
        if id_player not in self.ids_players:
            self.ids_players.append(id_player)

    def start_game(self):
        if self.status != 'lobby':
            raise ActionImpossibleNow('The game has already started.')
        # check number of player
        if len(self.ids_players) not in [4, 5, 6] and not self.debug:
            raise NumberPlayersError("There must be between 4 and 6 players.")
        shuffle(self.ids_players)
        shuffle(self.pile)
        self.hands = {x: [] for x in self.ids_players}
        self.ids_players_turn_generator = cycle(self.ids_players)
        self.current_turn = {
            'id_player_storyteller': next(self.ids_players_turn_generator),
            'table': OrderedDict(),
            'description': None,
            'votes': {},
        }
        for _ in range(0, 6):
            self._distribute()
        self.status = 'tell'

    def get_hand(self, id_player):
        self._sanity_check(id_player=id_player)
        return self.hands[id_player]

    def tell(self, id_player, id_card, description):
        self._sanity_check(id_player=id_player, id_card=id_card)
        if self.status != 'tell':
            raise ActionImpossibleNow("Impossible to tell at this stage")
        if id_player != self.current_turn['id_player_storyteller']:
            raise PlayerError("Only the storyteller can vote")
        if len(description) <= 2:
            raise DescriptionError("Description should not be empty")
        self.hands[id_player].remove(id_card)
        # self.current_turn['id_player_storyteller'] = id_player
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
            raise PlayerError("The storyteller cannot play")
        if id_player in self.current_turn['table']:
            raise PlayerError("You have already played a card")
        self.hands[id_player].remove(id_card)
        self.current_turn['table'][id_player] = id_card
        if len(self.current_turn['table']) == len(self.ids_players):
            self.status = 'vote'
            # shuffle table
            items = list(self.current_turn['table'].items())
            shuffle(items)
            self.current_turn['table'] = OrderedDict(items)

    def get_table(self):
        if self.status not in ['vote', 'end_turn', 'end_game']:
            return []  # return empty list if table is updated before vote
        return list(self.current_turn['table'].values())

    def vote(self, id_player, id_card):
        """
        Other players vote for one of the card on the table
        :param id_player:
        :param id_card:
        :return: True if all other players have cast their vote
        """
        self._sanity_check(id_player=id_player)  # do not check that id_card is in hand of player
        if self.status != 'vote':
            raise ActionImpossibleNow("Impossible to vote at this stage")
        if id_player == self.current_turn['id_player_storyteller']:
            raise PlayerError("The storyteller cannot vote")
        if id_card == self.current_turn["table"][id_player]:
            raise CardError("You cannot vote for your own card")
        if id_card not in self.current_turn['table'].values():
            raise CardError("Card not in table")
        self.current_turn['votes'][id_player] = id_card
        if len(self.current_turn['votes']) == len(self.ids_players) - 1:
            self._update_points_with_current_turn()
            self.status = 'end_turn'

    def _update_points_with_current_turn(self):
        if len(self.current_turn['table']) != len(self.ids_players):
            raise ValueError("Some cards missing")
        if len(self.current_turn['votes']) != len(self.ids_players) - 1:
            raise ValueError("Not all players has voted")
        points_current_turn = Counter()
        id_player_storyteller = self.current_turn['id_player_storyteller']
        # list of players except storyteller
        ids_players_others = self.ids_players.copy()
        ids_players_others.remove(id_player_storyteller)
        # count number of votes for the storyteller's card
        id_card_storyteller = self.current_turn['table'][id_player_storyteller]
        id_players_vote_for_storyteller = [k for k, v in self.current_turn['votes'].items() if
                                           v == id_card_storyteller]
        # if all other players or nobody voted the storyteller's card, add 2 points for other players
        if len(id_players_vote_for_storyteller) in [0, len(ids_players_others)]:
            for id_player in ids_players_others:
                points_current_turn[id_player] += 2
        # else, add +3 points to storyteller and to others players that vote for storyteller's card
        else:
            points_current_turn[id_player_storyteller] += 3
            for id_player in id_players_vote_for_storyteller:
                # 3 points for others players who correctly guessed
                points_current_turn[id_player] += 3
        # add +1 point for each vote for other players' cards
        id_players_vote_not_storyteller = list(set(ids_players_others) - set(id_players_vote_for_storyteller))
        for id_player in id_players_vote_not_storyteller:
            # for each player who didn't vote for the storyteller, add 1 point to the card owner
            id_player_owner_list = [k for k, v in self.current_turn['table'].items() if
                                    v == self.current_turn['votes'][id_player]]
            if len(id_player_owner_list) != 1:
                raise RuntimeError("Could not extract who place the card")
            points_current_turn[id_player_owner_list[0]] += 1

        self._points += points_current_turn
        self.current_turn['points'] = points_current_turn

    def end_turn(self):
        # save current turn
        self.past_turns.append(self.current_turn)
        # distribute new cards
        try:
            self._distribute()
        except GameEndedError:
            self.status = 'end_game'
            return
        # set next storytellers
        self.current_turn = {
            'id_player_storyteller': next(self.ids_players_turn_generator),
            'table': OrderedDict(),
            'description': None,
            'votes': {},
        }
        self.status = 'tell'

    def get_last_turn(self):
        if len(self.past_turns) < 1:
            return None
        return self.past_turns[-1]

    @property
    def points(self):
        return {k: self._points[k] for k in self.ids_players}
