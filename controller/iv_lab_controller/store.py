from typing import Union


class Store(object):
    """
    A global data store making it easy to access information anywhere from
    within the app.

    > See https://stackoverflow.com/questions/6760685/creating-a-singleton-in-python
    """
    _instance: Union['Store', None] = None

    def __new__(cls, *args, **kwargs):
        """
        Singleton class constructor.
        """
        if cls._instance is None:
            cls._instance = object.__new__(cls, *args, **kwargs)

        return cls._instance

    @staticmethod
    def put(cls, key, value):
        pass
