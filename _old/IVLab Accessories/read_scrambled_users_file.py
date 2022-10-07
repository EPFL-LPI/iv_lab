import os
import sys
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

args = sys.argv # get the arguments

# need at least one for the filename
if len(args) < 2:
	print("ERROR: This scripts expects a user file name as an argument\n")
	sys.exit()

filename = args[1]

#filename = os.getcwd() + r"\scrambled_users.json"

f = open(filename, "r")
scrambled_string = f.read()
json_string = unscramble_string(scrambled_string)
json_data = json.loads(json_string)
user_table = json_data
print(user_table)
