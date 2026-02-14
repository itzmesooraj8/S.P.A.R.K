from dotenv import load_dotenv
load_dotenv()
from spark.integrations.ears_stream import DeepgramStreamer

if __name__ == "__main__":
    def show_partial(text):
        print("[PARTIAL]", text)
    def show_final(text):
        print("[FINAL]", text)
    print("Speak into your microphone. Partial and final transcriptions will appear below:")
    DeepgramStreamer().listen_stream(show_partial, show_final)
