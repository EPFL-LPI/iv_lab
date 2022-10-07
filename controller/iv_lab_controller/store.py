from abc import ABC
from enum import Enum
from typing import Any, Callable, Dict, List



class Subscriber(ABC):
    """
    Subscriber to the store.
    """
    def subscribed(self, value: Any):
        """
        Called when the subscriber is first subscribed to a key.

        :param value: Current value of key's data.
        """
        pass

    def change(self, value: Any, o_value: Any):
        """
        Called when a key's data the subscriber is 
        subscribed to changes.

        :param value: New value of key's data.
        :param o_value: Old value of key's data.
        """
        pass

    def removed(self, value: Any):
        """
        Called when a key the subscriber is subscribed to
        is removed from the store.

        :param value: Current value of key's data.
        """
        pass


 class StoreValue(Enum):
     """
     Special values for the store.
     """
     Undefined = 0


class Store():
    """
    A global data store making it easy to access information
    anywhere from within the app.
    """
    _store: Dict[str, Any] = {}
    _subscribers: Dict[str, List[Subscriber]] = {}

    @classmethod
    def put(cls, key: str, value: Any):
        """
        Insert or update a key value.
        Calls subscribers to `key`.
        
        :param key: Data key.
        :param value: Value to set for the key.
        """
        o_value = (
            cls._store[key]
            if key in cls._store else
            StoreValue.Undefined
        )

        cls._store[key] = value
        
        # subscribers
        if key not in cls._subscribers:
            cls._subscribers[key] = []

        for s in cls._subscribers[key]:
            s.change(value, o_value)

    @classmethod
    def get(cls, key: str) -> Any:
        """
        Gets the value for the given key.

        :param key: Data key.
        :returns: Data associated with the given key.
        :raises KeyError: If the key does not exist in the store.
        """
        return cls._store[key]

    @classmethod
    def remove(cls, key: str):
        """
        Remove a key, its data, and subscribers from the store.

        If `key` does not exist in the store, returns silently. 

        :param key: Key to remove.
        """
        if key not in cls._store:
            return

        value = cls._store[key]
        for s in cls._subscribers[key]:
            s.removed(value)

        del cls._store[key]

    @classmethod
    def has(cls, key: str) -> bool:
        """
        :returns: `True` if the given key exists in the store,
            otherwise `False`.
        """
        return key in cls._store

    @classmethod
    def subscribe(cls, key: str, subscriber: Subscriber):
        """
        Adds a subcriber function to be called when the 
        given key is updated.

        :param key: Key to subscribe to.
        :param fcn: Function to call when key is updated.
        :raises KeyError: if the given key does not exist in the store.
        """
        if key not in cls._subscribers:
            raise KeyError(key)

        cls._subscribers[key].append(subscriber)
        subscriber.subscribed(cls._store[key])
