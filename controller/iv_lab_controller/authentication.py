import os
from pathlib import Path
from typing import Union, List
import json

from iv_lab_controller.user import User

from . import common


def user_list() -> List[User]:
    """
    :return: List of user objects.
    """
    app_dir = common.app_data_folder()
    users_path = os.path.join(app_dir, 'users.json')

    # ensure file exists
    if not os.path.exists(app_dir):
        Path(app_dir).mkdir(parents = True)
    
    if not os.path.exists(users_path):
        with open(users_path, 'w') as f:
            f.write('[]')

    # load users
    with open(users_path) as f:
        users = json.load(f)

    users = list(map(lambda u: User(**u), users))
    return users


def get_user_by_name(username: str, users: list) -> Union[User, None]:
    """
    :param username: Username to search for.
    :param users: List of user objects.
    :returns: User object by name or None if not found.
    :raises ValueError: If multiple users found.
    """
    found = list(filter(lambda u: (u.username == username.lower()), users))
    if len(found) == 0:
        return None

    if len(found) > 1:
        raise ValueError(f'Multiple users found with username `{username}`.')

    return found[0]


def authenticate(username: str, pwd: str) -> Union[User, None]:
    """
    Authenticates a username-password pair.

    :param username: Username.
    :param pwd: Cleartext password.
    :returns: User if valid user is found and authenticated, None otherwise.
    """
    username_std = username.lower()
    users = user_list()
    user = get_user_by_name(username, users)

    # verify if username and password match
    if (user is None) or (user.password != pwd):
        return None

    return user