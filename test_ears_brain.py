from spark.integrations.voice import VoiceIO
from spark.modules import brain

def main():
    ears = VoiceIO()
    print("Say something to S.P.A.R.K....")
    user_text = ears.transcribe()
    if user_text:
        print("\nS.P.A.R.K. is thinking...")
        answer = brain.think(user_text)
        print("\n--- S.P.A.R.K. Responds ---")
        print(answer)
        print("-------------------------")
    else:
        print("Sorry, I couldn't hear you.")

if __name__ == "__main__":
    main()
