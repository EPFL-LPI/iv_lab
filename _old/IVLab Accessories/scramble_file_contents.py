import os
import sys
import random

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
	print("Error: this script expects a filename as input\n")
	sys.exit()

fname = args[1]

#open the scrambled file and store contents as a string
f = open(fname, "r")
fileString = f.read()
f.close()

#extract the filename from the path and create a new path/filename in the current directory
basePath, filename = os.path.split(fname)
scrambled_filename = "scrambled_" + filename
scrambled_path = os.getcwd() + "\\" + scrambled_filename

#save the unscrambled file
f = open(scrambled_path, "w")
f.write(scramble_string(fileString))
f.close()