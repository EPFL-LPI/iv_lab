import os
import json

users = {"username":"Sciper", 
        "legeyt":"180578" }

filename = os.getcwd() + "\\" + "users.json"

with open(filename, 'w') as outfile:
    json.dump(users, outfile)