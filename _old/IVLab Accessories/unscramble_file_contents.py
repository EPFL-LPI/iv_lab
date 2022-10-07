import os
import sys

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
	print("Error: this script expects a filename as input\n")
	sys.exit()

fname = args[1]

#open the scrambled file and store contents as a string
f = open(fname, "r")
fileString = f.read()
f.close()

#extract the filename from the path, unscramble it and create a new path/filename in the current directory
basePath, filename = os.path.split(fname)
unscrambled_filename = "unscrambled_" + filename
unscrambled_path = os.getcwd() + "\\" + unscrambled_filename

#save the unscrambled file
f = open(unscrambled_path, "w")
f.write(unscramble_string(fileString))
f.close()