from spark.integrations.voice import VoiceIO

if __name__ == "__main__":
    ears = VoiceIO()
    ears.transcribe()
