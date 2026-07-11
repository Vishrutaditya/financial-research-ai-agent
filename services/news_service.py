from newsapi import NewsApiClient
from utils.config import NEWS_API_KEY

newsapi = NewsApiClient(api_key=NEWS_API_KEY)


def get_company_news(company_name, page_size=5):
    try:
        news = newsapi.get_everything(
            q=f'"{company_name}"',
            language="en",
            sort_by="publishedAt",
            page_size=page_size
        )

        return news["articles"]

    except Exception as e:
        print(f"Error fetching news: {e}")
        return []