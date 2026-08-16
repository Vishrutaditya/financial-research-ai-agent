from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Initialize VADER Sentiment Analyzer
analyzer = SentimentIntensityAnalyzer()


def analyze_sentiment(text):
    """
    Analyze the sentiment of a news article.
    Returns Positive, Negative, or Neutral.
    """

    score = analyzer.polarity_scores(text)

    if score["compound"] >= 0.05:
        return "Positive ✅"

    elif score["compound"] <= -0.05:
        return "Negative ❌"

    else:
        return "Neutral 😐"