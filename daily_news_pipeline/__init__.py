# This file makes Python treat the directory as a package
# Import all scraper modules to make them available when importing from daily_news_pipeline
from .news_scrapers.daily_scraper_all_hiphop import all_hiphop_scraper
from .news_scrapers.daily_scraper_hiphopdx import hiphopdx_scraper
from .news_scrapers.daily_scraper_okay_player import okayplayer_scraper
from .news_scrapers.daily_scraper_rapradar import rapradar_scraper
from .news_scrapers.daily_scraper_hotnewhiphop import hotnew_hiphop
from .news_scrapers.daily_scraper_hiphop_1987 import hiphop_1987_scraper
from .news_scrapers.daily_scraper_hiphop_hero import hiphophero_scraper
from .news_scrapers.daily_scraper_rap_up import rap_up_scraper

__all__ = [
    'all_hiphop_scraper',
    'hiphopdx_scraper',
    'okayplayer_scraper',
    'rapradar_scraper',
    'hotnew_hiphop',
    'hiphop_1987_scraper',
    'hiphophero_scraper',
    'rap_up_scraper'
]
