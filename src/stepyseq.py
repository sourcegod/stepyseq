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
import miditools
_pa = pyaudio.PyAudio()

class SampleObj(object):
    def __init__(self, freq=0, _len=0):
        self.freq = freq
        self.note =0
        self.data_len = _len
        self.raw_data = None
  
    #-------------------------------------------

#========================================


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
    def __init__(self, rate=44100, channels=1, _len=1):
        self._rate = rate
        self._channels = channels
        self._len = _len

    #-------------------------------------------

    def gen_samples(self, freq=440, _len=0):
        if _len == 0:
            _len = self._len
        nb_samples = int(_len * self._rate)
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
        self._sampLst = [] # [0] * self._nbNotes
        self._paramLst = []
        self._audioData = None
    
    #-------------------------------------------

   
    def get_bpm(self):
        return self._bpm

    #-------------------------------------------

    def set_bpm(self, bpm):
        if bpm >= self._minBpm and bpm <= self._maxBpm:
            self._bpm = bpm
            self._tempo = float(self._nbClockMsec / self._bpm) # in millisec
            self._nbSamples = int( (self._tempo * self._rate / 1000) * (4 / self._nbNotes) ) # in samples
            # self.gen_audio()
     
    #-------------------------------------------
 
    def get_freq(self, index):
        try:
            return self._sampLst[index].freq
        except IndexError:
            return 0
    
    #-------------------------------------------

    def set_freq(self, index, freq):
        if freq >= 0 and freq <= 20000:
            try:
                self._sampLst[index].freq = freq
            except IndexError:
                pass
    
    #-------------------------------------------

    def get_note(self, index):
        try:
            return self._sampLst[index].note
        except IndexError:
            return 0
    
    #-------------------------------------------

    def set_note(self, index, note):
        if note >= 0 and note <= 127:
            try:
                self._sampLst[index].note = note
            except IndexError:
                pass
    
    #-------------------------------------------
  
    def set_sample(self, index, samp):
        try:
            self._sampLst[index] = samp
            # self.gen_audio()
        except IndexError:
            pass
 
    #-------------------------------------------

    def get_sample(self, index):
        try:
            return self._sampLst[index]
        except IndexError:
            return 
 
    #-------------------------------------------
      
    def set_sampleList(self, samp_lst):
        """ init sample list """
        self._sampLst = samp_lst

    #-------------------------------------------

    def get_sampleList(self):
        return self._sampLst

    #-------------------------------------------

    def gen_audio(self):
        audioData = []
        samp_lst = self.get_sampleList()
        for samp in samp_lst:
            audioData.extend(samp.raw_data[0:self._nbSamples])
        
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
        _len =2 # in sec
        self._waveGen = WaveGenerator(self._rate, self._channels, _len)
        self._midTools = miditools
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
        pat.set_sampleList(sampLst)
        
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
        samp_lst = []
        midnote_lst = [72, 76, 79, 84]    
        for note in midnote_lst:
            freq = self._midTools.mid2freq(note) # C5
            samp_obj = SampleObj(freq=freq, _len=samp_len)
            samp_obj.note = note
            samp_obj.raw_data = self._waveGen.gen_samples(samp_obj.freq, samp_obj.data_len)
            samp_lst.append(samp_obj)

        """
        sampLst = [self._waveGen.gen_samples(880, samp_len),
                self._waveGen.gen_samples(440, samp_len),
                self._waveGen.gen_samples(560, samp_len),
                self._waveGen.gen_samples(700, samp_len),
                ]
        """
        pat.set_sampleList(samp_lst)

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
        self._pat.gen_audio()
        self.init_params()
        msg = f"Bpm: {bpm}"
        self.print_info(msg)

    #-------------------------------------------

    def change_freq(self, index, freq, inc=0, msg=None):
        assert self._pat
        if inc == 1: # is incremental
            freq = self._pat.get_freq(index) + freq
            pass

        samp_len =2 # in sec
        samp_obj = self._pat.get_sample(index) # SampleObj(freq, samp_len)
        assert samp_obj
        samp_obj.freq = freq
        samp_obj.raw_data = self._waveGen.gen_samples(freq, samp_len)
        self._pat.gen_audio()
        self.init_params()
        freq = self._pat.get_freq(index)
        if msg is None:
            msg = f"Freq: {freq}"
        self.print_info(msg)

    #-------------------------------------------

    def change_note(self, index, note, inc=0):
        assert self._pat
        if inc == 1: # is incremental
            note = self._pat.get_note(index) + note

        self._pat.set_note(index, note)
        freq = self._midTools.mid2freq(note)
        msg = f"Note: {note}"
        self.change_freq(index, freq, inc=0, msg=msg)
        # self.print_info(msg)

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
        self.print_info("Play Start")
        
    #-------------------------------------------

    def play_pause(self):
        if self._playing: 
            self._audioDriver.stop()
            self._playing = False
            self._pausing = True
            self.print_info("Pause")
        elif not self._playing or self._pausing:
            self._audioDriver.start()
            self._playing = True
            self._pausing = False
            self.print_info("Play")

    #-------------------------------------------
    
    def stop(self):
        if self._playing or self._pausing:
            self._audioDriver.stop()
            self.init_pos()
            self._playing = False
            self._pausing = False
            self.print_info("Stop")
        
    #-------------------------------------------
 
    def print_info(self, info):
        assert self._pat
        print(info)

    #-------------------------------------------


#========================================


def main():
    audi_man = AudioManager()
    audi_man.init_audioDriver()
    audi_man.init_pattern()
    valStr = ""
    savStr = ""
    while 1:
        key = param1 = param2 = ""
        valStr = input("-> ")
        if valStr == '': valStr = savStr
        else: savStr = valStr
        if valStr == " ":
            key = valStr
        else:
            lst = valStr.split()
            lenLst = len(lst)
            if lenLst >0: key = lst[0]
            if lenLst >1: param1 = lst[1]
            if lenLst >2: param2 = lst[2]

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
        elif key == 'sb':
            audi_man.change_bpm(10, inc=1)
        elif key == 'sB':
            audi_man.change_bpm(-10, inc=1)
        elif key == 'bpm':
            if param1:
                audi_man.change_bpm(float(param1), inc=0) # not incremental
            else:
                audi_man.change_bpm(120, 0)
        elif key == "freq":
            if not param1: param1 =0
            if not param2: param2 =440
            audi_man.change_freq(int(param1), float(param2), inc=0) # not incremental
        elif key == 'sf':
            if not param1: param1 =0
            audi_man.change_freq(int(param1), 10, inc=1)
        elif key == 'sF':
            if not param1: param1 =0
            audi_man.change_freq(int(param1), -10, inc=1)


        elif key == "note":
            if not param1: param1 =0
            if not param2: param2 =69 # A4
            audi_man.change_note(int(param1), int(param2), inc=0) # not incremental
        elif key == "sn":
            if not param1: param1 =0
            audi_man.change_note(int(param1), 1, inc=1)
        elif key == "sN":
            if not param1: param1 =0
            audi_man.change_note(int(param1), -1, inc=1)


#-------------------------------------------

if __name__ == "__main__":
    main()

