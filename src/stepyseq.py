#! /usr/bin/env python3
"""
    File: stepyseq.py
    Prototype for Step Sequencer
    Date: Mon, 15/11/2021
    Author: Coolbrother
"""

import os
import math
import time
import numpy as np
import pyaudio
from collections import deque
import miditools
import timeit
import readline
import curses


_pa = pyaudio.PyAudio()

_HISTORY_TEMPFILE = "/tmp/.synth_history"

def read_historyfile(filename=""):
    if not filename:
        filename = _HISTORY_FILENAME
    if os.path.exists(filename):
        readline.read_history_file(filename)
        # print('Max history file length:', readline.get_history_length())
        # print('Startup history:', get_history_items())

#------------------------------------------------------------------------------

def write_historyfile(filename=""):
    # print('Final history:', get_history_items())
    if not filename:
        filename = _HISTORY_FILENAME
    readline.write_history_file(filename)

#------------------------------------------------------------------------------


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
        arr = np.sin(2 * np.pi * freq * x / self._rate, dtype='float64') # in float only
        
        return arr

    #-------------------------------------------

    def gen_freq(self, arr, freq=440, _len=0):
        """ generate frequency for an array in place """
        if _len == 0:
            _len = self._len
        nb_samples = int(_len * self._rate)
        # init the  array in place
        # arr *= np.zeros(nb_samples, dtype='float32')
        arr *= 0
        x = np.arange(nb_samples)
        
        arr += np.sin(2 * np.pi * freq * x / self._rate, dtype='float64') # in float only
        # arr1 = np.sin(2 * np.pi * freq * x / self._rate, dtype='float64') # in float only
        # arr += arr1/2 # to be used later for effect
        # print(f"arr: {arr.dtype}")
        
        return arr

    #-------------------------------------------


#========================================

class Pattern(object):
    def __init__(self, bpm=120, rate=48000, nbNotes=4, sampLen=1):
        self._nbClockMsec = 60000 # in millisec
        self._minBpm = 10
        self._maxBpm = 600
        self._frameCount = 960
        self._rate = rate # in samples
        self._nbNotes = nbNotes
        self._sampLen = sampLen # in sec
        if bpm >= self._minBpm and bpm <= self._maxBpm:
            self._bpm = bpm
        else:
            self._bpm = 120
        self._tempo = float(self._nbClockMsec / self._bpm) # in millisec
        self._nbSamples = int( (self._tempo * self._rate / 1000) * (4 / self._nbNotes) ) # in samples
        self._sampLst = [] # [0] * self._nbNotes
        self._paramLst = []
        self._frameLst = []
        self._byteLst = []
        self._sampIndex =0
        self._frameIndex =0
        self._transpose =0
        self._octave =4

        
        """
        self._nbTimes =0 # for repeating note
        self._restSamples =0
        self._nbCount =1
        self._restFrame = []
        """

        self._audioData = None
    
    #-------------------------------------------

   
    def get_bpm(self):
        return self._bpm

    #-------------------------------------------

    def set_bpm(self, bpm):
        if bpm < self._minBpm: bpm = self._minBpm
        elif bpm > self._maxBpm: bpm = self._maxBpm
        # TODO: make nbTimes and nbCount to sets bpm until 1 bpm with small sample data
        max_samples = int( self._sampLen * self._rate )
        tempo = float(self._nbClockMsec / bpm) # in millisec
        nb_samples = int( (tempo * self._rate / 1000) ) # in samples
        if nb_samples > max_samples:
            return
        self._nbSamples = int( nb_samples * (4 / self._nbNotes) ) # in samples
        self._tempo = tempo
        self._bpm = bpm

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

    def get_transpose(self):
        return self._transpose
    
    #-------------------------------------------

    def set_transpose(self, num):
        if num >=-12 and num <= 12:
            self._transpose = num
    
    #-------------------------------------------
    
    def get_octave(self):
        return self._octave
    
    #-------------------------------------------

    def set_octave(self, num):
        if num >=0 and num <=8:
            self._octave = num
    
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

    def set_frameList(self):
        # generate array of frames by reshaping
        frame_count = self._frameCount
        self._frameLst = []
        samp_lst = self._sampLst
        nb_samples = self._nbSamples
        # reshape accept only a multiple of frame_count
        (quo, rest) = divmod(nb_samples, frame_count)
        if rest: nb_samples -= rest
        for samp in samp_lst:
            # no copy, just numpy view slicing
            frame_arr = samp.raw_data[0:nb_samples].reshape(-1, frame_count)
            self._frameLst.append(frame_arr)
            # TODO: adding rest samples
   
    #-------------------------------------------

    def get_frameList(self):
        return self._frameLst

    #-------------------------------------------

    def gen_byteList(self):
        self._byteLst = []
        samp_lst = self.get_sampleList()
        nb_samples = self._nbSamples
        # reshape accept only a multiple of frame_count
        (quo, rest) = divmod(nb_samples, self._frameCount)
        if rest: nb_samples -= rest
        for samp in samp_lst:
            # no copy, just numpy view slicing
            row_lst = samp.raw_data[0:nb_samples].reshape(-1, self._frameCount)
            byte_lst = [np.float32(arr).tobytes() for arr in row_lst]
            self._byteLst.append(byte_lst)
        
        return self._byteLst

    #-------------------------------------------

    def get_byteList(self):
        return self._byteLst

    #-------------------------------------------


    def gen_audio(self):
        data_lst = []
        nb_samples = self._nbSamples
        self.set_frameList()
        # self.gen_byteList()
        samp_lst = self.get_sampleList()
        for samp in samp_lst:
            data_lst.append(samp.raw_data[0:nb_samples])
        
        audio_data = np.float32(data_lst).tobytes()
        self._audioData = audio_data
        
        return audio_data

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
        self._curPat = None # for pattern
        self._playing = False
        self._pausing = False
        self._sampIndex =0
        self._sampChanged =0
        self._isMixing =1
        self._vol =1
        self._durLst = [0, 1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64]
        self._quantLen =0
        self._quantIndex =0

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

    def get_bufData(self):
        if len(self._deqData):
            return self._deqData.popleft()

    #-------------------------------------------
    
    def poll_audio(self):
        assert self._audioData
        step = self._index + self._frameBytes # frame_count * 4 # 4 for float size
        try:
            if step >= self._dataLen:
                self._index =0
            data = self._audioData[self._index:step]
            self._index += self._frameBytes
            return data

        except IndexError:
            pass


    #-------------------------------------------

    def render_audio1(self):
        """ First implementation """
        nb_data =4
        if len(self._deqData) > nb_data/2: return
        samp_lst = self._curPat.get_sampleList()
        while 1:
            if len(self._deqData) >= nb_data: break
            if self._sampIndex >= len(samp_lst):
                self._sampIndex =0
            samp = samp_lst[self._sampIndex]
            raw_data = samp.raw_data[0:self._curPat._nbSamples]
            step = self._index + self._frameCount
            
            try:
                if step >= len(raw_data):
                    self._index =0
                    self._sampIndex +=1
                audioData = samp.raw_data[self._index:step]
                self._index += self._frameCount
                audioData = np.float32(audioData).tobytes()
                self._deqData.append(audioData)
            except IndexError:
                pass
        
    #-------------------------------------------

    def render_audio2(self):
        """ 2nd implementation """
        nb_data =4
        if self._sampChanged or self._sampIndex == 0:
            self._deqData.clear()
        elif not self._sampChanged and len(self._deqData) > nb_data/2: 
            return

        samp_lst = self._curPat.get_sampleList()
        if self._sampIndex >= len(samp_lst):
            self._sampIndex =0
        # print(f"sampIndex: {self._sampIndex}, len deq: {len(self._deqData)}")
        samp = samp_lst[self._sampIndex]
        nb_samples = self._curPat._nbSamples
        # reshape accept only a multiple of frame_count
        (quo, rest) = divmod(nb_samples, self._frameCount)
        if rest: nb_samples -= rest
        # no copy, just numpy view slicing
        raw_data = samp.raw_data[0:nb_samples].reshape(-1, self._frameCount)
        
        # print("Len deq before loop: ", len(self._deqData))
        
        # """
        for audio_data in raw_data:
            self._deqData.append(
                    np.float32(audio_data).tobytes()
                    )
        # """
        # print("Len deq after loop: ", len(self._deqData))
        self._sampIndex +=1
        self._sampChanged =0

    #-------------------------------------------

    def render_audio(self):
        """
        render_audio3
        3nd implementation with deque object 
        """
        cur_pat = self._curPat
        frame_lst = cur_pat.get_frameList()
        if not frame_lst: return
        samp_index = cur_pat._sampIndex
        frame_index = cur_pat._frameIndex
        nb_data =2
        if len(self._deqData) > nb_data/2: return

        # print(f"First sampIndex: {samp_index}, Len frame_lst: {len(frame_lst)}")
        # print(f"frame_index: {frame_index}")
        index_starting = samp_starting =0

        if samp_index >= len(frame_lst): 
            frame_arr = frame_lst[0]
            # samp_starting =1
        else:
            frame_arr = frame_lst[samp_index]
        
        if frame_index >= len(frame_arr): 
            audio_data = frame_arr[0]
        else:
            audio_data = frame_arr[frame_index]

        while 1:
            if len(self._deqData) >= nb_data: break
           
            if frame_index >= len(frame_arr):
                frame_index =0
                cur_pat._frameIndex = frame_index
                index_starting =1
            
            if index_starting:

                if samp_index >= len(frame_lst) -1:
                    samp_index =0
                    cur_pat._sampIndex = samp_index
                else:
                    samp_index +=1
                    cur_pat._sampIndex = samp_index
                    samp_starting =1
                    index_starting =0
    
            try:
                audio_data = frame_arr[frame_index]
                if self._isMixing:
                    audio_data = self.get_mixData(frame_index, audio_data)
                audio_data = np.float32(audio_data).tobytes()
                self._deqData.append(audio_data)
                # print("Len deq after loop: ", len(self._deqData))
                frame_index +=1
                cur_pat._sampIndex = samp_index
                cur_pat._frameIndex = frame_index
                samp_starting =0

            except IndexError:
                pass

    #-------------------------------------------

    def get_mixData(self, index, data):
        """ transform audio data """
        data = data.copy()
        if self._quantLen:
            self.set_quantizeLen(index, data)
        data *= self._vol
        
        return data
    #-------------------------------------------

    def render_audio4(self):
        """ 4nd implementation with deque object and bytes string list """
        byte_lst = self._curPat.get_byteList()
        if not byte_lst: return
        nb_data =2
        if len(self._deqData) > nb_data/2: return

        # print(f"First sampIndex: {self._sampIndex}, Len byte_lst: {len(byte_lst)}")
        
        index_changed = samp_changed =0
        if self._sampIndex >= len(byte_lst): 
            row_lst = byte_lst[0]
            samp_changed =1
        else:
            row_lst = byte_lst[self._sampIndex]
        
        if self._index >= len(row_lst): 
            audio_data = row_lst[0]
            index_changed =1
        else:
            audio_data = row_lst[self._index]

        while 1:
            if len(self._deqData) >= nb_data: break
            
            if self._index >= len(row_lst):
                self._index =0
                if self._sampIndex >= len(byte_lst) -1:
                    self._sampIndex =0
                else:
                    self._sampIndex +=1
                samp_changed =1
            
            try:
                row_lst = byte_lst[self._sampIndex]
                audio_data = row_lst[self._index]
                self._deqData.append(audio_data)
                # print("Len deq after loop: ", len(self._deqData))
                self._index +=1
                samp_changed =0

            except IndexError:
                pass

    #-------------------------------------------



    def is_audioReady(self):
        # Deprecated
        return len(self._deqData)
    
    #-------------------------------------------

    def _func_callback(self, in_data, frame_count, time_info, status):
        # print("frame_count: ", frame_count)
        data = None
        
        # data = self.poll_audio()
        # print("len deque: ", len(self._deqData))
        self.render_audio()
        data = self.get_bufData() 
        
        return (data, pyaudio.paContinue)

    #-------------------------------------------

    def init_pattern(self, bpm=120):
        """ create new pattern and returns audio data """
        audioData = []
        samp_len =6 # in secs
        pat = Pattern(bpm, sampLen=samp_len)
        samp_lst = []
        midnote_lst = [60, 64, 67, 72]    
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
        
        self._curPat = pat
        self.init_params()

        
        return audioData

    #-------------------------------------------

    def get_data(self):
        audioData = []
        if self._curPat is None:
            audioData = self.init_pattern()
       
        return audioData

    #-------------------------------------------
    
    def change_bpm(self, bpm, adding=0):
        if not self._curPat: return
        cur_bpm = self._curPat.get_bpm()
        if adding == 1: # is incremental
            bpm += cur_bpm

        self._curPat.set_bpm(bpm)
        self._curPat.gen_audio()
        self.init_params()
        cur_bpm = self._curPat.get_bpm()
        msg = f"Bpm: {cur_bpm}"
        self.print_info(msg)

    #-------------------------------------------

    def change_freq(self, index, freq, adding=0, msg=None):
        assert self._curPat
        if adding == 1: # is incremental
            freq = self._curPat.get_freq(index) + freq
            pass

        samp_obj = self._curPat.get_sample(index) # SampleObj(freq, samp_len)
        assert samp_obj
        samp_obj.freq = freq
        samp_len = samp_obj.data_len 
        # change samp_obj.raw_data in place
        # samp_obj.raw_data = 
        self._waveGen.gen_freq(samp_obj.raw_data, freq, samp_len)
        # print(f"raw_data: {samp_obj.raw_data.dtype}")
        self._curPat.gen_audio()
        self.init_params()
        freq = self._curPat.get_freq(index)
        if msg is None:
            msg = f"Freq: {freq}"
        self.print_info(msg)

    #-------------------------------------------

    def change_note(self, index, note, adding=0):
        assert self._curPat
        if adding == 1: # is incremental
            note = self._curPat.get_note(index) + note
            # print("val note: ", note)

        self._curPat.set_note(index, note)
        freq = self._midTools.mid2freq(note)
        msg = f"Note: {note}"
        self.change_freq(index, freq, adding=0, msg=msg)
        # self.print_info(msg)

    #-------------------------------------------

    def change_transpose(self, num, adding=0):
        assert self._curPat
        if adding == 1:
            val = self._curPat.get_transpose() + num
        else: # not incremental
            val = num 
            num -= self._curPat.get_transpose()
        if val >=-12 and val <=12:
            samp_lst = self._curPat.get_sampleList()
            self._curPat.set_transpose(val)
            for (index, samp) in enumerate(samp_lst):
                note = self._curPat.get_note(index)
                note += num
                self._curPat.set_note(index, note)
                freq = self._midTools.mid2freq(note)
                self.change_freq(index, freq, adding=0, msg="")
            
        
        note = self._curPat.get_note(0)
        val = self._curPat.get_transpose()
        msg = f"Transpose: {val}, Note: {note}"
        self.print_info(msg)

    #-------------------------------------------

    def change_octave(self, num, adding=0):
        assert self._curPat
        if adding == 1:
            val = self._curPat.get_octave() + num
        else: # not incremental
            val = num 
            num -= self._curPat.get_octave()
        if val >=0 and val <=8:
            samp_lst = self._curPat.get_sampleList()
            self._curPat.set_octave(val)
            num *= 12 # 12 notes by  octave
            for (index, samp) in enumerate(samp_lst):
                note = self._curPat.get_note(index)
                note += num
                self._curPat.set_note(index, note)
                freq = self._midTools.mid2freq(note)
                self.change_freq(index, freq, adding=0, msg="")
            
        
        note = self._curPat.get_note(0)
        val = self._curPat.get_octave()
        msg = f"Octave: {val}, Note: {note}"
        self.print_info(msg)

    #-------------------------------------------

    def change_volume(self, num, adding=0):
        assert self._curPat
        if adding == 1:
            num += self._vol
        if num >=0 and num <=1:
            self._vol = num
       
        vol = self._vol 
        msg = f"Volume: {vol:.1f}"
        self.print_info(msg)

    #-------------------------------------------

    def change_quantizeLen(self, num, adding=0):
        assert self._curPat
        quant_index = self._quantIndex
        if adding == 1:
            quant_index += num
        else:
            try: 
                quant_index = self._durLst.index(num)
            except ValueError:
                quant_index = -1
        
        if quant_index >=0 and quant_index < len(self._durLst):
            nb_samples = self._curPat._nbSamples
            self._quantLen = self._durLst[quant_index]
            self._quantIndex = quant_index
       
        quant_len = self._quantLen
        msg = f"Quantize len: {quant_len}"
        self.print_info(msg)

    #-------------------------------------------

    def set_quantizeLen(self, index, audio_data):
      
        quant_len = self._quantLen
        if quant_len >1:
            nb_samples = int(self._curPat._nbSamples / quant_len)
            quant_index = int(nb_samples / self._frameCount)
            if index >= quant_index:
                audio_data *= 0
        """
        msg = f"Quantize index: {quant_index}"
        self.print_info(msg)
        """


    #-------------------------------------------



    def init_pos(self):
        if not self._curPat: return
        self._index =0
        self._sampIndex =0
        self._curPat._frameIndex =0
        self._curPat._sampIndex =0

    #-------------------------------------------

    def init_params(self):
        if self._curPat:
            self._audioData = self._curPat.get_audioData()
            self._dataLen = len(self._audioData)
            self.init_pos()
            self._sampChanged =1

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
        print(info)

    #-------------------------------------------
    
    def perf(self, nb_times=1_000_000, nb_repeats=7):
        """
        using the timeit module for short function
        Note: poll_audio is faster than render_audio, when calling with arguments.
        But, it is the inverse result when calling with no arguments
        WHY???
        """


        # nb_times = 1_000_000
        # nb_repeats =7
        func1 = """ 
def f():
    return self.poll_audio()
"""

        func2 = """ 
def f():
    self.render_audio()
    data = self.get_bufData()
"""


        """
        val = timeit.timeit(stmt=func1, number=1000000)
        print(f"poll_audio time: {val}")
        val = timeit.timeit(stmt=func2, number=1000000)
        print(f"render_audio time: {val}")
        """

        time_lst = timeit.repeat(stmt=func1, number=nb_times, repeat=nb_repeats)
        print("min time for poll_audio: {:0.6f}".format(min(time_lst)))
        time_lst = timeit.repeat(stmt=func2, number=nb_times, repeat=nb_repeats)
        print("min time for render_audio:  {:0.6f}".format(min(time_lst)))
         # """


    #-----------------------------------------

 
    def test(self):
        print("Test\n")
        
        nb_times = 1_000_000
        nb_repeats =7
        self.perf(nb_times, nb_repeats)
        
    #-------------------------------------------

#========================================

class CommandLine(object):
    def __init__(self):
        self.audi_man = None
   
    #-------------------------------------------

    def set_audiMan(self, audi_man):
        self.audi_man = audi_man

    #-------------------------------------------

    def mainloop(self):
        filename = _HISTORY_TEMPFILE
        read_historyfile(filename)

        valStr = ""
        savStr = ""

        try:
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
                    self.audi_man.stop()
                    self.audi_man.close_audioDriver()
                    break

                elif key == 'p':
                    self.audi_man.play()
                elif key == 's':
                    self.audi_man.stop()
                elif key == ' ':
                    self.audi_man.play_pause()

                elif key == "bpm":
                    if not param1: param1 = 120
                    self.audi_man.change_bpm(float(param1), adding=0) # not incremental
                elif key == 'sb':
                    if not param1: param1 =10
                    self.audi_man.change_bpm(float(param1), adding=1)
                elif key == 'sB':
                    if not param1: param1 =-10
                    self.audi_man.change_bpm(float(param1), adding=1)

                elif key == "freq":
                    if not param1: param1 =0
                    if not param2: param2 =440
                    self.audi_man.change_freq(int(param1), float(param2), adding=0) # not incremental
                elif key == 'sf':
                    if not param1: param1 =0
                    if not param2: param2 = 10
                    self.audi_man.change_freq(int(param1), float(param2), adding=1)
                elif key == 'sF':
                    if not param1: param1 =0
                    if not param2: param2 = -10
                    self.audi_man.change_freq(int(param1), float(param2), adding=1)

                elif key == "note":
                    if not param1: param1 =0
                    if not param2: param2 =69 # A4
                    self.audi_man.change_note(int(param1), int(param2), adding=0) # not incremental
                elif key == "sn":
                    if not param1: param1 =0
                    if not param2: param2 =1
                    self.audi_man.change_note(int(param1), int(param2), adding=1)
                elif key == "sN":
                    if not param1: param1 =0
                    if not param2: param2 =-1
                    self.audi_man.change_note(int(param1), int(param2), adding=1)

                elif key == "trs":
                    if not param1: param1 =0
                    self.audi_man.change_transpose(int(param1), adding=0) # not incremental
                elif key == "st":
                    if not param1: param1 =1
                    self.audi_man.change_transpose(int(param1), adding=1)
                elif key == "sT":
                    if not param1: param1 =-1
                    self.audi_man.change_transpose(int(param1), adding=1)
                
                elif key == "oct":
                    if not param1: param1 =4
                    self.audi_man.change_octave(int(param1), adding=0) # not incremental
                elif key == "so":
                    if not param1: param1 =1
                    self.audi_man.change_octave(int(param1), adding=1)
                elif key == "sO":
                    if not param1: param1 =-1
                    self.audi_man.change_octave(int(param1), adding=1)

                elif key == "vol":
                    if not param1: param1 =1
                    self.audi_man.change_volume(float(param1), adding=0) # not incremental
                elif key == "sv":
                    if not param1: param1 =0.1
                    self.audi_man.change_volume(float(param1), adding=1)
                elif key == "sV":
                    if not param1: param1 =-0.1
                    self.audi_man.change_volume(float(param1), adding=1)
  
                elif key == "quant":
                    if not param1: param1 =1
                    self.audi_man.change_quantizeLen(int(param1), adding=0)
                elif key == "sq":
                    if not param1: param1 =1
                    self.audi_man.change_quantizeLen(int(param1), adding=1)
                elif key == "sQ":
                    if not param1: param1 =-1
                    self.audi_man.change_quantizeLen(int(param1), adding=1)
                 
                elif key == "tt":
                    self.audi_man.perf()
                elif key == "test":
                    self.audi_man.test()
        finally:
            write_historyfile(filename)

    #-------------------------------------------

#========================================

class MainWindow(object):
    def __init__(self):
        self.stdscr = curses.initscr()
        curses.noecho() # don't repeat key hit at the screen
        # curses.cbreak()
        # curses.raw() # for no interrupt mode like suspend, quit
        curses.start_color()
        curses.use_default_colors()
        self.ypos =0; self.xpos =0
        self.height, self.width = self.stdscr.getmaxyx()
        self.win = curses.newwin(self.height, self.width, self.ypos, self.xpos)
        self.win.refresh()
        self.win.keypad(1) # allow to catch code of arrow keys and functions keys
        self.audi_man = None

    #-------------------------------------------
   
    def display(self, msg=""):
        self.win.clrtoeol()
        self.win.refresh()
        # self.win.addstr(3, 0, "                                                           ")
        self.win.addstr(3, 0, str(msg))
        self.win.move(3, 0)
        self.win.refresh()

    #-------------------------------------------

    def close_win(self):
        curses.nocbreak()
        self.win.keypad(0)
        curses.echo()

    #-------------------------------------------

    def beep(self):
        curses.beep()

    #-------------------------------------------

    def set_audiMan(self, audi_man):
        self.audi_man = audi_man

    #-------------------------------------------

    def init_app(self):
        """
        init application
        from MainWindow object
        """

    #------------------------------------------------------------------------------
        
    def close_app(self):
        """
        close application
        from MainWindow object
        """
        pass

    #------------------------------------------------------------------------------

    def key_handler(self):
        msg = "Press a key..."
        self.display(msg)
        curses.beep() # to test the nodelay function
        while 1:
            key = self.win.getch()
            if key >= 32 and key < 128:
                key = chr(key)
            if key == 'Q':
                # self.audi_man.stop()
                # self.audi_man.close_audioDriver()
                self.close_app()
                self.close_win()
                self.beep()
                break

            elif key == 9: # Tab key
                pass

            elif key == 27: # Escape for key
                self.beep()

            elif key == 'p':
                # self.audi_man.play()
                pass
            elif key == 's':
                # self.audi_man.stop()
                pass
            elif key == ' ':
                # self.audi_man.play_pause()
                pass

            elif key == ':': #
                pass

            elif key == 20: # ctrl+T
                msg = "Test"
                self.display(msg)
                self.test()
   
    #-------------------------------------------
    
    def mainloop(self):
        self.init_app()
        self.key_handler()

    #-------------------------------------------

    def test(self):
        self.beep()
            
    #------------------------------------------------------------------------------

#========================================


class MainApp(object):
    def __init__(self):
        self.audi_man = AudioManager()
        self._com = CommandLine()
        self._win = None
        # self._win = MainWindow()

    #-------------------------------------------
   
    def init_app(self):
        """
        init application
        from MainApp object
        """
        self.audi_man.init_audioDriver()
        self.audi_man.init_pattern()
        self._com.set_audiMan(self.audi_man)
        # self._win.set_audiMan(self.audi_man)

    #------------------------------------------------------------------------------
        
    def close_app(self):
        """
        close application
        from MainApp object
        """
        pass

    #------------------------------------------------------------------------------

   
    def main(self):
        self.init_app()
        self._com.mainloop()

    #-------------------------------------------

    def test(self):
        pass
            
    #------------------------------------------------------------------------------

#========================================

if __name__ == "__main__":
    app = MainApp()
    app.main()
#------------------------------------------------------------------------------

