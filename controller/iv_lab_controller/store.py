from enum import Enum
from typing import Any, Dict, Set, Callable, Union


class Observer():
    """
    Observer to the store.
    """
    def __init__(
        self,
        subscribed: Union[Callable, None] = None,
        changed: Union[Callable, None] = None,
        removed: Union[Callable, None] = None,
    ):
        """
        :param subscribed: Function to call for subscribed.
        :param changed: Function to call for changed.
        :param removed: Function to call for removed.
        """
        if subscribed is not None:
            self.__setattr__('subscribed', subscribed)

        if changed is not None:
            self.__setattr__('changed', changed)

        if removed is not None:
            self.__setattr__('removed', removed)


    def subscribed(self, value: Any):
        """
        Called when the observer is first subscribed to a key.

        :param value: Current value of key's data.
        """
        pass

    def changed(self, value: Any, o_value: Any):
        """
        Called when a key's data the observer is 
        subscribed to changes.

        :param value: New value of key's data.
        :param o_value: Old value of key's data.
        """
        pass

    def removed(self, value: Any):
        """
        Called when a key the observer is subscribed to
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
    _observers: Dict[str, Set[Observer]] = {}
    _listeners: Dict[str, Set[Callable]] = {}

    # --- observers ---
    @classmethod
    def set(cls, key: str, value: Any):
        """
        Insert or update a key value.
        Calls observers of `key`.
        
        :param key: Data key.
        :param value: Value to set for the key.
        """
        o_value = (
            cls._store[key]
            if key in cls._store else
            StoreValue.Undefined
        )

        cls._store[key] = value
        
        # observers
        if key not in cls._observers:
            cls._observers[key] = set()

        for s in cls._observers[key]:
            s.changed(value, o_value)

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
        Remove a key and its data, and observers from the store.
        If `key` does not exist in the store, returns silently. 

        :param key: Key to remove.
        """
        cls.remove_key(key)
        cls.clear_observers(key)

    @classmethod
    def remove_key(cls, key: str):
        """
        Removes the key and its associated data from the store.
        If the key does not exist, exits quietly.
        Does not affect the key's observers.

        :param key: Key to remove from the store.
        """
        if key not in cls._store:
            return

        value = cls._store[key]
        for s in cls._observers[key]:
            s.removed(value)

        del cls._store[key]

    @classmethod
    def clear_observers(cls, key: str):
        """
        Removes all observers from a key.
        Does not affect the key's data.
        """
        if key in cls._observers:
            del cls._observers[key]

    @classmethod
    def has(cls, key: str) -> bool:
        """
        :returns: `True` if the given key exists in the store,
            otherwise `False`.
        """
        return key in cls._store

    @classmethod
    def subscribe(cls, key: str, observer: Observer):
        """
        Adds an observer to the given key.
        Subscribing is idempotent, meaning an observer may only be added once to a key.
        Observers may subscribe to keys before they exist in the store.

        :param key: Key to subscribe to.
        :param observer: Observer.
        """
        if key not in cls._observers:
            cls._observers[key] = set()

        cls._observers[key].add(observer)

        # run subscribed
        value = (
            cls._store[key]
            if key in cls._store else
            StoreValue.Undefined
        )

        observer.subscribed(value)

    @classmethod
    def unsubscribe(cls, key: str, observer: Observer):
        """
        Removes a observer from the given key.
        If `key` does not exist, or `observer` was not subscribed to `key`,
        returns silently.

        :param key: Key to remove the `observer` from.
        :param observer: Observer to remove.
        """
        if key not in cls._observers:
            return

        try:
            cls._observers[key].remove(observer)

        except KeyError:
            pass

    # --- listeners ---
    @classmethod
    def on(cls, topic: str, listener: Callable):
        """
        Adds a listener for the given topic.
        This is an idempotent function, meaning adding the same listener
        to the same topic multiple times will have not additional effects.

        :param topic: Topic to listen to.
        :param listener: Callable to run when topic emits.
        """
        if topic not in cls._listeners:
            cls._listeners[topic] = set()

        cls._listeners[topic].add(listener)

    @classmethod
    def ignore(cls, topic: str, listener: Callable):
        """
        Remove a listener from the given topic.
        If `listener` was not listening to `topic`, fails silently.

        :param topic: Topic to search.
        :param listener: Callable to remove.
        """
        if topic in cls._listeners:
            cls._listeners[topic].remove(listener)

    @classmethod
    def emit(cls, topic: str, *args, **kwargs):
        """
        Emits a signal to listeners of the topic.

        :param topic: Topic to emit to.
        :param *args: Positional arguments passed to the listeners.
        :param **kwargs: Keyword arguments passed to the listeners.
        """
        if topic not in cls._listeners:
            return

        for listener in cls._listeners[topic]:
            listener(*args, **kwargs)


