import logging
whisper_there = False
try:
    import whisper
    whisper_there = True
except: logging.warning('whisper not installed')
