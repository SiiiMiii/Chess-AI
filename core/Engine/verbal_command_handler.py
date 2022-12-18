import http.client as httplib
from contextlib import contextmanager
import sys, os
try:
    import speech_recognition as sr
except ImportError as e:
    print("ERROR: Cannot find module 'speech_recognition.' Speech activation command utitlity will be deactivated.")
    print("Try run `pip install pyaudio` and `pip install SpeechRecognition`")


def is_internet_connected(ip_adresses: tuple=("8.8.8.8", "8.8.4.4")) -> bool:
    """
    :param ip_adresses: Goggle's public DNS servers. Helps avoiding DNS resolution, 
    application layer connections and calls to external utilities from Python.
    """
    for ip in ip_adresses:
        connection = httplib.HTTPSConnection(ip, timeout=5)
        try:
            connection.request("HEAD", "/")
            return True
        except Exception:
            continue
        finally:
            connection.close()

@contextmanager
def silence_function():
    """
    surpresses console output of a function called within the context manager
    """
    with open(os.devnull, "w") as devNull:
        initial = sys.stdout
        sys.stdout = devNull
        try: yield
        finally: sys.stdout = initial

class VerbalCommandHandler:
    """
    Handles speech-to-text and determines whether user is calling for AI to overtake the thinking
    """

    activation_keywords = {"difficult", "position", "think", "let", "clueless", "i", "don't know", "i am", "i'm", "desperate", "uncertain", "god", "help"}
    
    @classmethod
    def init(cls, keywords: list | tuple=None, activation_threshold=2):
        """
        :param activation_threshold: the number of keywords that has to be met in oder for the search to start
        """
        try:
            cls.recognizer = sr.Recognizer()
        except Exception as e:
            print("ERROR:", e, "You might have to install missing modules. Make sure all requirements are met")
        else:
            cls.recognizer.pause_threshold = .5
        cls.activation_keywords = keywords or cls.activation_keywords
        cls.activation_threshold = activation_threshold

    @classmethod
    def speech_to_text(cls) -> str | None:
        try:
            # Using standard mic input
            with sr.Microphone() as source:
                print("Listening...")
                audio = cls.recognizer.listen(source)
            if not is_internet_connected():
                raise ConnectionError("status code 404. Not Found. Please connect to internet for using speech-to-text.")
            with silence_function(): # This is to suppress the internal console outputs of recognize_google
                # Where the magic happens
                text = cls.recognizer.recognize_google(audio)
            return text
        except Exception as e:
            print("ERROR:", str(e))

    @classmethod
    def listen_for_activation(cls):
        commands = cls.speech_to_text()
        commands = commands.lower()
        print(commands)
        keyword_counter = 0
        for kw in cls.activation_keywords:
            if kw in commands:
                keyword_counter += 1
        return keyword_counter >= cls.activation_threshold