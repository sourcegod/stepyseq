#! /usr/bin/python3
"""
    Utils functions for midi notes number, notes names, and frequencies.
    Date: Tue, 14/09/2021
    Author: Coolbrother
"""

# Midi notes numbers: from 0 to 127
# Midi notes names: from C-1 to G9

_note_names = [
            'C', 'C#', 'D', 'D#',
            'E', 'F', 'F#', 
            'G', 'G#', 'A', 'A#', 'B'
            ]

_note_lst = []
_freq_lst = []

def limit_value(val, min_val=0, max_val=127):
    if val < min_val: return min_val
    if val > max_val: return max_val
    return val

#-----------------------------------------

def _init_noteList():
    """ initializing notes list """
    global _note_lst
    _note_lst = [name + str(i) for i in range(-1, 10) for (j, name) in enumerate(_note_names) if (i+1)*12+j <= 127]
    return _note_lst

#-----------------------------------------

def _init_noteFreq():
    """ initializing notes and freqs list """
    global _note_lst, _freq_lst
    _note_lst = []; _freq_lst = []
    count =0
    for i in range(-1, 10):
        for name in _note_names:
            _note_lst.append(name + str(i))
            _freq_lst.append(mid2freq(count))
            count += 1
            if count > 127:
                return

#-----------------------------------------

def mid2freq(val):
    """ returns freq from midi note number """
    ref = 440.0/32 # 13.75 Hz, note A-1
    # we substract -9 for getting C-1 note name
    return ref * pow(2, (int(val) - 9) * 1/12.0)

#-----------------------------------------

def mid2note(val):
    """ convert midi number to note name """
    try:
        val = limit_value(val, 0, 127)
        return _note_lst[val]
    except IndexError:
        return ""

#-----------------------------------------

def note2mid(name):
    """ convert note name to midi note number """
    try:
        return _note_lst.index(name.upper())
    except IndexError:
        return 0

#-----------------------------------------

def note2freq(name):
    """ convert note name to freq """
    try:
        val = _note_lst.index(name.upper())
        return _freq_lst[val]
    except IndexError:
        return 0

#-----------------------------------------

# initializing note freq dic
_init_noteFreq()
def test():
    hz = note2freq
    print("Test on midutils\n")
    print("Note names list:")
    for (i, item) in enumerate(_note_lst):
        print(f"{i}: {item}", end=", ")
        print()
    for (name, freq) in zip(_note_lst, _freq_lst):
        print(f"{name}: {freq}")

    print(f"Note to Mid A4: {note2mid('a4')}")
    print(f"Note to Freq A3: {hz('a3')}")
    print("Midi Input count: ", get_input_count())
    print("Midi Output count: ", get_output_count())

#-----------------------------------------

if __name__ == "__main__":
    test()
    input("Pres Enter...")
