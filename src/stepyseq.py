#! /usr/bin/env python3
"""
    File: stepyseq.py
    Prototype for Step Sequencer
    Date: Mon, 15/11/2021
    Author: Coolbrother
"""

import math
import time
import numpy as np
import pyaudio
from collections import deque
_pa = pyaudio.PyAudio()

class BaseDriver(object):
    def __init__(self):
        self._rate = 48000
        self._channels =1
        self._frameCount =960
        self._frameBytes = self._frameCount * 4 # in float, so 4 bytes
   
    #-------------------------------------------

#========================================

class PortDriver(BaseDriver):
    """ Port Audio Driver """
    def __init__(self):
        super().__init__()
        self._stream = None
        self._func_callback = None

    #-------------------------------------------

    def set_streamCallback(self, func):
        self._func_callback = func

    #-------------------------------------------

    def open_stream(self):
        self._stream = _pa.open(
                    rate = self._rate,
                    channels = self._channels,
                    # format=pyaudio.paInt16,
                    format = pyaudio.paFloat32,
                    output=True,
                    frames_per_buffer = self._frameCount, # 960
                    start = False, # starting the callback function 
                    stream_callback = self._func_callback
                    )

    #-------------------------------------------
   
    def init_driver(self):
        self.open_stream()

    #-------------------------------------------

    def write(self, samp):
        assert self._stream
        self._stream.write(samp)

    #-------------------------------------------

    def start(self):
        if not self._stream: return
        self._stream.start_stream()
       
    #-------------------------------------------

    def stop(self):
        if not self._stream: return
        self._stream.stop_stream()
       
    #-------------------------------------------
    
    def close(self):
        if self._stream:
            self._stream.close()
            _pa.terminate()

    #-------------------------------------------
    
#========================================

class WaveGenerator(object):
    """ generate waveform """
    def __init__(self, rate=44100, channels=1):
        self._rate = rate
        self._channels = channels

    #-------------------------------------------

    def gen_samples(self, freq=440, length=1):
        # freq = 440
        # rate = 48000
        # length =1 # length samples
        nb_samples = int(length * self._rate)
        # create an array
        x = np.arange(nb_samples)
        # the math function, is also the final sample
        arr = np.sin(2 * np.pi * freq * x / self._rate) # in float only
        
        return arr

    #-------------------------------------------

#========================================

class Pattern(object):
    def __init__(self, bpm=120, rate=48000, nbNotes=4):
        self._nbClockMsec = 60000 # in millisec
        self._minBpm = 30
        self._maxBpm = 600
        self._rate = rate # in samples
        self._nbNotes = nbNotes
        if bpm >= self._minBpm and bpm <= self._maxBpm:
            self._bpm = bpm
        else:
            self._bpm = 120
        self._tempo = float(self._nbClockMsec / self._bpm) # in millisec
        self._nbSamples = int( (self._tempo * self._rate / 1000) * (4 / self._nbNotes) ) # in samples
        self._noteLst = [] # [0] * self._nbNotes
        self._audioData = None
    
    #-------------------------------------------

    def set_bpm(self, bpm):
        if bpm >= self._minBpm and bpm <= self._maxBpm:
            self._bpm = bpm
        self._tempo = float(self._nbClockMsec / self._bpm) # in millisec
        self._nbSamples = int( (self._tempo * self._rate / 1000) * (4 / self._nbNotes) ) # in samples
        self.gen_audio()
 
    #-------------------------------------------
    
    def get_bpm(self):
        return self._bpm

    #-------------------------------------------

    
    def add_notes(self, *notes):
        """ adding notes to the list """
        self._noteLst.extend(notes)

    #-------------------------------------------

    def get_notes(self):
        return self._noteLst

    #-------------------------------------------

    def gen_audio(self):
        audioData = []
        sampLst = self.get_notes()
        for samp in sampLst:
            audioData.extend(samp[0:self._nbSamples])
        
        audioData = np.float32(audioData).tobytes()
        self._audioData = audioData
        
        return audioData

    #-------------------------------------------

    def get_audioData(self):
        return self._audioData

    #-------------------------------------------


#========================================

class AudioManager(BaseDriver):
    def __init__(self):
        super().__init__()
        self._audioDriver = PortDriver()
        self._waveGen = WaveGenerator(self._rate, 1)
        self._audioData = None
        self._dataLen =0
        self._deqData = deque()
        self._deqIndex =0
        self._index =0
        self._pat = None # for pattern
        self._playing = False
        self._pausing = False

    #-------------------------------------------

    def init_audioDriver(self):
        self._audioDriver.set_streamCallback(self._func_callback)
        self._audioDriver.init_driver()

    #-------------------------------------------

    def close_audioDriver(self):
        self._audioDriver.close()

    #-------------------------------------------

    def write_data(self):
        smp = []
        pat = Pattern()
        sampLst = [self._waveGen.gen_samples(880, 1),
                self._waveGen.gen_samples(440, 1),
                self._waveGen.gen_samples(560, 1),
                self._waveGen.gen_samples(700, 1),
                ]
        pat.add_notes(*sampLst)
        
        for samp in sampLst:
            smp.extend(samp[0:24000])
        smp = np.float32(smp).tobytes()
        while 1:
            self._audioDriver.write(smp)

    #-------------------------------------------

    def _func_callback(self, in_data, frame_count, time_info, status):
        # print("frame_count: ", frame_count)
        data = None
        if self._audioData is None:
            print("Initialize Data")
            # self._audioData = self.get_data()
            return (data, None)
        # print("len data: ", len(self._audioData))
        step = self._index + self._frameBytes # frame_count * 4 # 4 for float size
        try:
            if step >= self._dataLen:
                self._index =0
            data = self._audioData[self._index:step]
            self._index += self._frameBytes

        except IndexError:
            pass

        return (data, pyaudio.paContinue)

    #-------------------------------------------

    def init_pattern(self, bpm=120):
        """ create new pattern and returns audio data """
        audioData = []
        pat = Pattern(bpm)
        samp_len =2 # in secs
        sampLst = [self._waveGen.gen_samples(880, samp_len),
                self._waveGen.gen_samples(440, samp_len),
                self._waveGen.gen_samples(560, samp_len),
                self._waveGen.gen_samples(700, samp_len),
                ]
        pat.add_notes(*sampLst)

        audioData = pat.gen_audio()
        
        self._pat = pat
        self.init_params()

        
        return audioData

    #-------------------------------------------

    def get_data(self):
        audioData = []
        if self._pat is None:
            audioData = self.init_pattern()
       
        return audioData

    #-------------------------------------------
    
    def change_bpm(self, bpm, inc=0):
        if not self._pat: return
        if inc == 1: # is incremental
            bpm = self._pat.get_bpm() + bpm

        self._pat.set_bpm(bpm)
        self.init_params()

    #-------------------------------------------

    
    def init_pos(self):
        if not self._pat: return
        self._index =0

    #-------------------------------------------

    def init_params(self):
        if self._pat:
            self._audioData = self._pat.get_audioData()
            self._dataLen = len(self._audioData)
            self._index =0

    #-------------------------------------------

    def play(self):
        # self.write_data()
        self.init_pos()
        self._audioDriver.start()
        self._playing = True
        
    #-------------------------------------------

    def play_pause(self):
        if self._playing: 
            self._audioDriver.stop()
            self._playing = False
            self._pausing = True
        elif not self._playing or self._pausing:
            self._audioDriver.start()
            self._playing = True
            self._pausing = False

    #-------------------------------------------
    
    def stop(self):
        if self._playing or self._pausing:
            self._audioDriver.stop()
            self.init_pos()
            self._playing = False
            self._pausing = False
        
    #-------------------------------------------
 
    def print_info(self, info):
        if not self._pat: return
        if info == "bpm":
            val = self._pat.get_bpm()
            print(f"Bpm:  {val}")

    #-------------------------------------------


#========================================


def main():
    audi_man = AudioManager()
    audi_man.init_audioDriver()
    audi_man.init_pattern()
    sav_key = ''
    while 1:
        key = input("-> ")
        if key == '': key = sav_key
        else: sav_key = key
        if key == 'q':
            print("Bye Bye!!!")
            audi_man.stop()
            audi_man.close_audioDriver()
            break

        elif key == 'p':
            audi_man.play()
        elif key == 's':
            audi_man.stop()
        elif key == ' ':
            audi_man.play_pause()
        elif key == 'f':
            audi_man.change_bpm(10, inc=1)
            audi_man.print_info("bpm")
        elif key == 'F':
            audi_man.change_bpm(-10, inc=1)
            audi_man.print_info("bpm")
        elif key == 'ff':
            audi_man.change_bpm(120, inc=0) # not incremental
            audi_man.print_info("bpm")
#-------------------------------------------

if __name__ == "__main__":
    main()

