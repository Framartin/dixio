from random import shuffle
from itertools import cycle
from collections import Counter

NB_CARDS = 84


class GameEndedError(Exception):
    pass

class NumberPlayersError(ValueError):
    pass

class NotReadyToVoteError(Exception):
    pass


class DixitGame:

    def __init__(self, ids_players):
        if len(ids_players) not in [4,5,6]:
            raise NumberPlayersError("There must be between 4 and 6 players.")
        shuffle(ids_players)
        self.ids_players = ids_players
        self.pile = list(range(1, NB_CARDS+1))
        shuffle(self.pile)
        self.hands = {x: [] for x in ids_players}
        self.ids_players_turn_generator = cycle(ids_players)
        self.current_turn = {
            'id_player_storyteller': next(self.ids_players_turn),
            'table': {},
            'description': None,
            'votes': {},
        }
        self.past_turns = []
        self.points = Counter()
        for _ in range(0, 6):
            self._distribute()

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
        if id_player != self.current_turn['id_player_storyteller']:
            raise ValueError("Only the storyteller can vote")
        self.hands[id_player].remove(id_card)
        self.current_turn['id_player_storyteller'] = id_player
        self.current_turn['description'] = description
        self.current_turn['table'][id_player] = id_card

    def play(self, id_player, id_card):
        """
        Other players choose a card to place on the table
        :param id_player:
        :param id_card:
        :return: True if all players have played
        """
        self._sanity_check(id_player=id_player, id_card=id_card)
        if id_player == self.current_turn['id_player_storyteller']:
            raise ValueError("The storyteller cannot play")
        self.hands[id_player].remove(id_card)
        self.current_turn['table'][id_player] = id_card
        return len(current_turn['table']) == len(self.ids_players)

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
        return len(self.current_turn['vote']) == len(self.ids_players)-1

    def _update_points_with_current_turn(self):
        if len(current_turn['table']) != len(self.ids_players):
            raise ValueError("Some cards missing")
        if len(self.current_turn['vote']) != len(self.ids_players)-1:
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
                    id_player_owner_list = [k for k, v in self.current_turn['table'].items() if v == self.current_turn['vote'][id_player]]
                    if len(id_player_owner_list) != 1:
                        raise RuntimeError("Could not extract who place the card")
                    points_current_turn[id_player_owner_list[0]] += 1
        self.points += points_current_turn
        self.current_turn['points'] = points_current_turn

    def end_turn(self):
        # update points
        self._update_points_with_current_turn()
        # save current turn
        self.past_turns.append(self.current_turn)
        # set next storytellers
        self.current_turn = {
            'id_player_storyteller': next(self.ids_players_turn_generator),
            'table': {},
            'description': None,
            'votes': {},
        }
        # distribute new cards
        self._distribute()

    def get_points_table_vote_last_turn(self):
        last_turn = self.past_turns[-1]
        return last_turn['points'], last_turn['table'], last_turn['vote']

    def get_stats(self):
        return {
            'points': self.points,
        }
