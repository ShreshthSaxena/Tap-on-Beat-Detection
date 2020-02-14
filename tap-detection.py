import pyaudio
import struct
import math
import time
from ffpyplayer.player import MediaPlayer
import numpy as np
import librosa


# y_beats = librosa.clicks(times= b)
# librosa.output.write_wav('metro.wav', y_beats, 22050)
# read a block of samples at a time, say 0.05 seconds worth
# compute the RMS amplitude of the block (square root of the average of the squares of the individual samples)
# if the block's RMS amplitude is greater than a threshold, it's a "noisy block" else it's a "quiet block"
# a sudden tap would be a quiet block followed by a small number of noisy blocks followed by a quiet block
# if you never get a quiet block, your threshold is too low
# if you never get a noisy block, your threshold is too high

INITIAL_TAP_THRESHOLD = 0.25
FORMAT = pyaudio.paInt16 
SHORT_NORMALIZE = (1.0/32768.0)
CHANNELS = 1
RATE = 44100  
INPUT_BLOCK_TIME = 0.05
INPUT_FRAMES_PER_BLOCK = int(RATE*INPUT_BLOCK_TIME)
# if we get this many noisy blocks in a row, increase the threshold
OVERSENSITIVE = 15.0/INPUT_BLOCK_TIME                    
# if we get this many quiet blocks in a row, decrease the threshold
UNDERSENSITIVE = 120.0/INPUT_BLOCK_TIME 
# if the noise was longer than this many blocks, it's not a 'tap'
MAX_TAP_BLOCKS = 0.15/INPUT_BLOCK_TIME

def get_rms( block ):
    # RMS amplitude is defined as the square root of the 
    # mean over time of the square of the amplitude.
    # so we need to convert this string of bytes into 
    # a string of 16-bit samples...

    # we will get one short out for each 
    # two chars in the string.
    count = len(block)/2
    format = "%dh"%(count)
    shorts = struct.unpack( format, block )

    # iterate over the block.
    sum_squares = 0.0
    for sample in shorts:
        # sample is a signed short in +/- 32768. 
        # normalize it to 1.0
        n = sample * SHORT_NORMALIZE
        sum_squares += n*n

    return math.sqrt( sum_squares / count )

class TapTester(object):
    def __init__(self):
        self.pa = pyaudio.PyAudio()
        self.stream = self.open_mic_stream()
        self.tap_threshold = INITIAL_TAP_THRESHOLD
        self.noisycount = MAX_TAP_BLOCKS+1 
        self.quietcount = 0 
        self.errorcount = 0

    def stop(self):
        self.stream.close()

    def find_input_device(self):
        device_index = None            
        for i in range( self.pa.get_device_count() ):     
            devinfo = self.pa.get_device_info_by_index(i)   
            print( "Device %d: %s"%(i,devinfo["name"]) )

            for keyword in ["mic","input"]:
                if keyword in devinfo["name"].lower():
                    print( "Found an input: device %d - %s"%(i,devinfo["name"]) )
                    device_index = i
                    return device_index

        if device_index == None:
            print( "No preferred input found; using default input device." )

        return device_index

    def open_mic_stream( self ):
        device_index = self.find_input_device()

        stream = self.pa.open(   format = FORMAT,
                                 channels = CHANNELS,
                                 rate = RATE,
                                 input = True,
                                 input_device_index = device_index,
                                 frames_per_buffer = INPUT_FRAMES_PER_BLOCK)

        return stream

    def tapDetected(self): #DETECTED
        print ("tapped")

    def listen(self):
        try:
            block = self.stream.read(INPUT_FRAMES_PER_BLOCK)
        except:
            # dammit. 
            self.errorcount += 1
            print( " Error recording: " )
            self.noisycount = 1
            return
        ret = 0
        amplitude = get_rms( block )
        if amplitude > self.tap_threshold:
            # noisy block
            self.quietcount = 0
            self.noisycount += 1
        else:            
            # quiet block.
            if 1 <= self.noisycount <= MAX_TAP_BLOCKS:
                self.tapDetected()
                ret = 1
            self.noisycount = 0
            self.quietcount += 1
        return ret

if __name__ == "__main__":
    bpm = input("enter beats per min")
    b = np.around(np.linspace(0,60,int(bpm)),decimals=2)
    y_beats = librosa.clicks(times= b)
    librosa.output.write_wav('metro.wav', y_beats, 22050)
    tt = TapTester()
    c = 0
    player = MediaPlayer('metro.wav')
    for i in range(1000):
    	# if tt.listen() == 1:
    	# 	if ((time.time()-start)% (2/3)) < 0.3:
    	# 		c += 1
    	# 		print("on beat")
    	# 		if c>1:
    	# 			print("streak x"+str(c))
    	# 	else:
    	# 		print("off beat")
    	# 		c = 0

    	if tt.listen() == 1:
    		if c == 0:
    			start = time.time()
    		if b[c]-0.1 <= round(time.time()-start,2) <= b[c]+0.1:
    			print("on beat x", str(c))
    			c+=1
    		else:
    			c=0

