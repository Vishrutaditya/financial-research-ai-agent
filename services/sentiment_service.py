from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

analyzer = SentimentIntensityAnalyzer()

texts = [
    "TCS reports excellent quarterly profits.",
    "TCS faces heavy losses this quarter.",
    "TCS announced a new office."
]

for text in texts:
    score = analyzer.polarity_scores(text)

    print("\nNews:", text)
    print("Score:", score)

    if score["compound"] >= 0.05:
        print("Positive ✅")

    elif score["compound"] <= -0.05:
        print("Negative ❌")

    else:
        print("Neutral ➖")