try:
    from newsapi import NewsApiClient
except ImportError:
    NewsApiClient = None

from utils.config import NEWS_API_KEY


def get_company_news(company_name, page_size=5):
    if not NEWS_API_KEY or NewsApiClient is None:
        return []
    try:
        newsapi = NewsApiClient(api_key=NEWS_API_KEY)
        news = newsapi.get_everything(
            q=f'"{company_name}"',
            language="en",
            sort_by="publishedAt",
            page_size=page_size
        )

        return news.get("articles", [])

    except Exception as e:
        print(f"Error fetching news: {e}")
        return []
