from newsapi import NewsApiClient
from utils.config import NEWS_API_KEY

newsapi = NewsApiClient(api_key="YOUR_NEWSAPI_KEY")

news = newsapi.get_everything(
    q="Tata Consultancy Services",
    language="en",
    sort_by="publishedAt",
    page_size=5
)
print(news["totalResults"])

print("Latest TCS News:\n")

for article in news["articles"]:
    print("Title:", article["title"])
    print("Source:", article["source"]["name"])
    print("Published:", article["publishedAt"])
    print("URL:", article["url"])
    print("-" * 50)