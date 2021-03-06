import abc
import json
import string
import hearthbreaker.constants


class JSONObject(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def __to_json__(self):
        pass

    @staticmethod
    @abc.abstractclassmethod
    def from_json(action, selector):
        pass

    def eq(self, other):
        return str(self) == str(other)

    def __str__(self):
        return json.dumps(self.__to_json__(), default=lambda o: o.__to_json__(), sort_keys=True)


class Aura(JSONObject):
    def __init__(self, status, selector):
        self.target = None
        self.status = status
        self.selector = selector

    def set_target(self, target):
        self.target = target

    def apply(self):
        targets = self.selector.get_targets(self.target)
        for target in targets:
            self.status.act(self.target, target)

    def unapply(self):
        targets = self.selector.get_targets(self.target)
        for target in targets:
            self.status.unact(self.target, target)

    def match(self, obj):
        return self.selector.match(self.target, obj)

    def __to_json__(self):
        return {
            'status': self.status,
            'selector': self.selector
        }

    @staticmethod
    def from_json(status, selector):
        status = Status.from_json(**status)
        selector = Selector.from_json(**selector)
        return Aura(status, selector)


class AuraUntil(Aura):
    def __init__(self, status, selector, until):
        super().__init__(status, selector)
        self.until = until

    def apply(self):
        super().apply()
        self.until.bind(self.target, self.__until__)

    def unapply(self):
        self.until.unbind(self.target, self.__until__)
        super().unapply()

    def __until__(self, *args):
        if isinstance(self.selector, hearthbreaker.tags.selector.SelfSelector):
            self.target.remove_aura(self)
        else:
            self.target.player.remove_aura(self)

    def __to_json__(self):
        return {
            'status': self.status,
            'selector': self.selector,
            'until': self.until
        }

    @staticmethod
    def from_json(status, selector, until):
        status = Status.from_json(**status)
        selector = Selector.from_json(**selector)
        until = Event.from_json(**until)
        return AuraUntil(status, selector, until)


class Player(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def get_players(self, target):
        pass

    @abc.abstractmethod
    def match(self, source, obj):
        pass

    @staticmethod
    def from_json(name):
        from hearthbreaker.tags.selector import FriendlyPlayer, EnemyPlayer, BothPlayer, PlayerOne,\
            PlayerTwo, CurrentPlayer, OtherPlayer
        if name == "friendly":
            return FriendlyPlayer()
        elif name == "enemy":
            return EnemyPlayer()
        elif name == "both":
            return BothPlayer()
        elif name == "player_one":
            return PlayerOne()
        elif name == "player_two":
            return PlayerTwo()
        elif name == "current_player":
            return CurrentPlayer()
        elif name == "other_player":
            return OtherPlayer()


class Picker(JSONObject, metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def pick(self, targets, player):
        pass

    @staticmethod
    def from_json(name, count=0):
        from hearthbreaker.tags.selector import UserPicker, AllPicker, RandomPicker
        if name == "user":
            return UserPicker()
        elif name == "all":
            return AllPicker()
        elif name == "random":
            return RandomPicker(count)
        else:
            raise TypeError("WHat are you even doing?")


class Selector(JSONObject, metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def get_targets(self, source, target=None):
        pass

    @abc.abstractmethod
    def match(self, source, obj):
        pass

    @staticmethod
    def from_json(name, **kwargs):
        import hearthbreaker.tags.selector as selector_mod

        cls_name = string.capwords(name, '_').replace("_", "") + "Selector"
        cls = getattr(selector_mod, cls_name)
        obj = cls.__new__(cls)
        return obj.__from_json__(**kwargs)

    def __from_json__(self, **kwargs):
        self.__init__(**kwargs)
        return self


class Action(JSONObject, metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def act(self, actor, target):
        pass

    @staticmethod
    def from_json(name, **kwargs):
        import hearthbreaker.tags.action as action_mod

        cls_name = string.capwords(name, '_').replace("_", "")
        cls = getattr(action_mod, cls_name)
        obj = cls.__new__(cls)
        return obj.__from_json__(**kwargs)

    def __from_json__(self, **kwargs):
        self.__init__(**kwargs)
        return self


class Status(JSONObject, metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def act(self, actor, target):
        pass

    @abc.abstractmethod
    def unact(self, actor, target):
        pass

    @staticmethod
    def from_json(name, **kwargs):
        import hearthbreaker.tags.status as status_mod

        cls_name = string.capwords(name, '_').replace("_", "")
        cls = getattr(status_mod, cls_name)
        obj = cls.__new__(cls)
        return obj.__from_json__(**kwargs)

    def __from_json__(self, **kwargs):
        self.__init__(**kwargs)
        return self


class StatusWithAmount(Status, metaclass=abc.ABCMeta):
    def __init__(self, amount, multiplier=1):
        self.amount = amount
        self.multipler = multiplier

    def read_amount(self, amount):
        if isinstance(amount, dict):
            return Selector.from_json(**amount)
        else:
            return amount

    def get_amount(self, source, target):
        if isinstance(self.amount, Selector):
            return len(self.amount.get_targets(source, target)) * self.multipler
        else:
            return self.amount

    def __to_json__(self, existing):
        existing['amount'] = self.amount
        if self.multipler != 1:
            existing['multiplier'] = self.multipler

        return existing

    def __from_json__(self, amount, **kwargs):
        kwargs['amount'] = self.read_amount(amount)
        return super().__from_json__(**kwargs)


class Event(JSONObject, metaclass=abc.ABCMeta):
    def __init__(self, event_name, condition=None):
        self.event_name = event_name
        self.condition = condition
        self.__func__ = None
        self.__target__ = None

    @abc.abstractmethod
    def bind(self, target, func):
        pass

    @abc.abstractmethod
    def unbind(self, target, func):
        pass

    def __action__(self, *args):
        if self.condition.evaluate(self.__target__, *args):
            self.__func__(*args)

    @staticmethod
    def from_json(event_name, **kwargs):
        import hearthbreaker.tags.event as event_mod

        cls_name = string.capwords(event_name, '_').replace("_", "")
        cls = getattr(event_mod, cls_name)
        obj = cls.__new__(cls)
        return obj.__from_json__(**kwargs)

    def __from_json__(self, condition=None):
        if condition:
            condition = Condition.from_json(**condition)
            self.__init__(condition)
        else:
            self.__init__()
        return self

    def __to_json__(self):
        if self.condition:
            return {
                'event_name': self.event_name,
                'condition': self.condition
            }
        return {
            'event_name': self.event_name
        }


class MinionEvent(Event):
    def bind(self, target, func):
        if self.condition:
            self.__target__ = target
            self.__func__ = func
            target.bind(self.event_name, self.__action__)
        else:
            target.bind(self.event_name, func)

    def unbind(self, target, func):
        if self.condition:
            target.unbind(self.event_name, self.__action__)
        else:
            target.unbind(self.event_name, func)


class PlayerEvent(Event):
    def __init__(self, event_name, condition, player):
        super().__init__(event_name, condition)
        self.player = player

    def bind(self, target, func):
        for player in self.player.get_players(target.player):
            if self.condition:
                self.__target__ = target
                self.__func__ = func
                player.bind(self.event_name, self.__action__)
            else:
                player.bind(self.event_name, func)

    def unbind(self, target, func):
        for player in self.player.get_players(target.player):
            if self.condition:
                player.unbind(self.event_name, self.__action__)
            else:
                player.unbind(self.event_name, func)

    def __to_json__(self):
        super_json = super().__to_json__()
        super_json.update({
            'player': self.player
        })
        return super_json

    def __from_json__(self, player, condition=None):
        if condition:
            condition = Condition.from_json(**condition)
        player = Player.from_json(player)
        self.__init__(condition, player)
        return self


class Effect(JSONObject):
    def __init__(self, event, action, selector):
        self.event = event
        if isinstance(action, Status):
            from hearthbreaker.tags.action import Give
            self.action = Give(action)
        else:
            self.action = action
        self.selector = selector
        self.target = None

    def apply(self):
        self.event.bind(self.target, self._find_target)

    def unapply(self):
        self.event.unbind(self.target, self._find_target)

    def set_target(self, target):
        self.target = target

    def _find_target(self, focus=None, other=None, *args):
        targets = self.selector.get_targets(self.target, focus)
        for target in targets:
            self.action.act(self.target, target)

    def __to_json__(self):
        return {
            'event': self.event,
            'action': self.action,
            'selector': self.selector,
        }

    @staticmethod
    def from_json(game, action, event, selector):
            action = Action.from_json(**action)
            event = Event.from_json(**event)
            selector = Selector.from_json(**selector)
            return Effect(event, action, selector)


class Condition(JSONObject, metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def evaluate(self, target, *args):
        pass

    @staticmethod
    def from_json(name, **kwargs):
        import hearthbreaker.tags.condition as action_mod

        cls_name = string.capwords(name, '_').replace("_", "")
        cls = getattr(action_mod, cls_name)
        obj = cls.__new__(cls)
        return obj.__from_json__(**kwargs)

    def __from_json__(self, **kwargs):
        self.__init__(**kwargs)
        return self

    @abc.abstractmethod
    def __to_json__(self):
        pass


class Deathrattle(JSONObject):
    def __init__(self, action, selector, condition=None):
        self.action = action
        self.selector = selector
        self.condition = condition

    def deathrattle(self, target):
        if self.condition:
            if not self.condition.evaluate(target):
                return
        targets = self.selector.get_targets(target, target)
        for t in targets:
            self.action.act(target, t)

        target.player.game.check_delayed()

    def __to_json__(self):
        if self.condition:
            return {
                'action': self.action,
                'selector': self.selector,
                'condition': self.condition,
            }
        return {
            'action': self.action,
            'selector': self.selector
        }

    @staticmethod
    def from_json(action, selector, condition=None):
        action = Action.from_json(**action)
        selector = Selector.from_json(**selector)
        if condition:
            condition = Condition.from_json(**condition)
        return Deathrattle(action, selector, condition)


class CARD_SOURCE:
    COLLECTION = 0
    MY_HAND = 1
    MY_DECK = 2
    OPPONENT_HAND = 3
    OPPONENT_DECK = 4
    LIST = 5
    LAST_SPELL = 6
    __sources = {
        "COLLECTION": COLLECTION,
        "MY_HAND": MY_HAND,
        "MY_DECK": MY_DECK,
        "OPPONENT_HAND": OPPONENT_HAND,
        "OPPONENT_DECK": OPPONENT_DECK,
        "LIST": LIST,
        "LAST_SPELL": LAST_SPELL,
    }

    @staticmethod
    def from_str(source_name):
        return CARD_SOURCE.__sources[source_name.upper()]

    @staticmethod
    def to_str(source_number):
        sources = dict(zip(CARD_SOURCE.__sources.values(), CARD_SOURCE.__sources.keys()))
        return sources[source_number].lower()


class CardQuery(JSONObject):
    def __init__(self, name=None, conditions=[], source=CARD_SOURCE.COLLECTION, source_list=None, make_copy=False):
        self.name = name
        self.conditions = conditions
        self.source = source
        self.source_list = source_list
        self.make_copy = make_copy

    def get_card(self, player):
        from hearthbreaker.game_objects import card_lookup, get_cards
        if self.name:
            return card_lookup(self.name)

        if self.source == CARD_SOURCE.COLLECTION:
            card_list = get_cards()
        elif self.source == CARD_SOURCE.MY_DECK:
            card_list = filter(lambda c: not c.drawn, player.deck.cards)
        elif self.source == CARD_SOURCE.MY_HAND:
            card_list = player.hand
        elif self.source == CARD_SOURCE.OPPONENT_DECK:
            card_list = filter(lambda c: not c.drawn, player.opponent.deck.cards)
        elif self.source == CARD_SOURCE.OPPONENT_HAND:
            card_list = player.opponent.hand
        elif self.source == CARD_SOURCE.LIST:
            card_list = self.source_list
        elif self.source == CARD_SOURCE.LAST_SPELL:
            return type(player.game.last_spell)()
        else:
            card_list = []
        # TODO Throw an exception in any other case?

        def check_condition(condition):
            return lambda c: condition.evaluate(player, c)

        for condition in self.conditions:
            card_list = filter(check_condition(condition), card_list)

        card_list = [card for card in card_list]
        card_len = len(card_list)
        if card_len == 1:
            chosen_card = card_list[0]
        elif card_len == 0:
            return None
        else:
            chosen_card = player.game.random_choice(card_list)

        if self.source == CARD_SOURCE.COLLECTION or self.source == CARD_SOURCE.LIST or self.make_copy:
            return chosen_card
        elif self.source == CARD_SOURCE.MY_DECK:
            chosen_card.drawn = True
            player.deck.left -= 1
            return chosen_card
        elif self.source == CARD_SOURCE.OPPONENT_DECK:
            chosen_card.drawn = True
            player.opponent.deck.left -= 1
            return chosen_card
        elif self.source == CARD_SOURCE.MY_HAND:
            player.hand.remove(chosen_card)
            return chosen_card
        elif self.source == CARD_SOURCE.OPPONENT_HAND:
            player.opponent.hand.remove(chosen_card)
            return chosen_card

    def __to_json__(self):
        json_obj = {}
        if self.name:
            json_obj['name'] = self.name
        else:
            if self.conditions is not None:
                json_obj['conditions'] = self.conditions
            if self.source is not None:
                json_obj['source'] = CARD_SOURCE.to_str(self.source)
            if self.source_list:
                json_obj['source_list'] = [card.name for card in self.source_list]
            if self.make_copy:
                json_obj['make_copy'] = self.make_copy

        return json_obj

    @staticmethod
    def from_json(name=None, conditions=[], source="collection", source_list=None, make_copy=False):
        from hearthbreaker.game_objects import card_lookup
        query = CardQuery.__new__(CardQuery)
        query.name = name
        query.conditions = []
        for condition in conditions:
            query.conditions.append(Condition.from_json(**condition))
        else:
            query.condition = None
        query.source = CARD_SOURCE.from_str(source)
        if source_list:
            query.source_list = [card_lookup(item) for item in source_list]
        else:
            query.source_list = None
        query.make_copy = make_copy
        return query


class Battlecry(JSONObject):
    def __init__(self, actions, selector, condition=None):
        if isinstance(actions, Action):
            self.actions = [actions]
        else:
            self.actions = actions
        self.selector = selector
        self.condition = condition

    def battlecry(self, target):
        if self.condition:
            if not self.condition.evaluate(target):
                return
        targets = self.selector.get_targets(target, target)
        for t in targets:
            for action in self.actions:
                action.act(target, t)

    def __to_json__(self):
        if self.condition:
            return {
                'actions': self.actions,
                'selector': self.selector,
                'condition': self.condition
            }
        return {
            'actions': self.actions,
            'selector': self.selector
        }

    @staticmethod
    def from_json(actions, selector, condition=None):
        actions = [Action.from_json(**action) for action in actions]
        selector = Selector.from_json(**selector)
        if condition:
            condition = Condition.from_json(**condition)
        return Battlecry(actions, selector, condition)


class Choice(Battlecry):
    def __init__(self, card, actions, selector, condition=None):
        self.card = card
        super().__init__(actions, selector, condition)

    def __to_json__(self):
        super_json = super().__to_json__()
        super_json['card'] = self.card.ref_name
        return super_json

    @staticmethod
    def from_json(card, actions, selector, condition=None):
        from hearthbreaker.game_objects import card_lookup
        actions = [Action.from_json(**action) for action in actions]
        selector = Selector.from_json(**selector)
        if condition:
            condition = Condition.from_json(**condition)
        card = card_lookup(card)
        return Choice(card, actions, selector, condition)


class Enrage(JSONObject):
    def __init__(self, statuses, selector):
        if isinstance(statuses, Status):
            self.statuses = [statuses]
        else:
            self.statuses = statuses
        self.selector = selector

    def enrage(self, target):
        targets = self.selector.get_targets(target, target)
        for t in targets:
            for status in self.statuses:
                status.act(target, t)

    def unenrage(self, target):
        targets = self.selector.get_targets(target, target)
        for t in targets:
            for status in self.statuses:
                status.unact(target, t)

    def __to_json__(self):
        return {
            'statuses': self.statuses,
            'selector': self.selector
        }

    @staticmethod
    def from_json(statuses, selector):
        statuses = [Status.from_json(**status) for status in statuses]
        selector = Selector.from_json(**selector)
        return Enrage(statuses, selector)
