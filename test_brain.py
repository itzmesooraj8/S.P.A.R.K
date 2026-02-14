from spark.modules.brain import SparkBrain

if __name__ == "__main__":
    brain = SparkBrain()
    user_text = input("Ask S.P.A.R.K.: ")
    reply = brain.ask(user_text)
    print("S.P.A.R.K.:", reply)
