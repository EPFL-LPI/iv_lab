import os
import sys
import random
import json

def unscramble_string(string_to_unscramble):   
    #un-scramble the numeric string
    hashedBytesExtracted = []
    for i in range(int(len(string_to_unscramble)/2)):
        hashedBytesExtracted.append(int(string_to_unscramble[i*2:(i+1)*2],16))
        
    #loop through the reversed array and un-do the random convolution, starting from the end and working back.
    HBElen = len(hashedBytesExtracted)
    unHashedBytesReversed = []
    for i, b in enumerate(hashedBytesExtracted):
        if i < HBElen-1:
            unHashedBytesReversed.append((hashedBytesExtracted[HBElen-1-i] - hashedBytesExtracted[HBElen-1-(i+1)]) % 256)
        else:
            pass #The last (first) byte is the random seed.  throw it out.
    
    #this is the string in byte form
    unHashedBytes = bytearray(list(reversed(unHashedBytesReversed)))
    
    return unHashedBytes.decode()

def scramble_string(string_to_scramble):
    #encode the string as a byte array
    bytename = bytearray(string_to_scramble.encode())
    #use single random byte to scramble the numeric 'string'.
    random.seed()
    randbyte = random.getrandbits(8)
    #add the random byte to the beginning, then scramble by making each byte equal to 
    #itself plus the byte before.  This way the random byte propagates through the whole array.
    hashedBytes = []
    hashedBytes.append(randbyte)
    for i, b in enumerate(bytename):
        hashedBytes.append((hashedBytes[i] + b) % 256)

    #turn the scrambled byte array back into a hexadecimal ascii string
    numericHash = ''
    for b in hashedBytes:
        numericHash = numericHash + '{:02x}'.format(b)
    
    return numericHash

args = sys.argv # get the arguments

# need at least one for the filename
if len(args) < 2:
	print("ERROR: This scripts expects a user file name as an argument\n")
	sys.exit()

filename = args[1]

#filename = os.getcwd() + r"\scrambled_users.json"
f = open(filename, "r")
scrambled_string = f.read()
f.close()
json_string = unscramble_string(scrambled_string)
json_data = json.loads(json_string)
user_table = json_data

username = input("Enter new user name: ")
if username in user_table:
    print("User " + username + " is already registered in the user table with sciper " + user_table[username])
    sys.exit()
sciper = input("Enter sciper for user " + username + ": ")
sure = input("Adding new user " + username + " with sciper " + sciper + ". Are you sure? (Y/N): ")
if sure == "Y" or sure == "y":
    user_table[username] = sciper
    #print("User Table:")
    #print(user_table)
    user_table_string = json.dumps(user_table)
    user_table_scrambled = scramble_string(user_table_string)
    f = open(filename, "w")
    f.write(user_table_scrambled)
    f.close()
