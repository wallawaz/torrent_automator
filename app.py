import argparse

from models.jackett import Jackett
from models.fetcher import EpisodeFetcher
from models.tvdb import TVDBAPI

from utils.config_parser import DEFAULTAPI, get_config_values


config_fp = "config.ini"

parser = argparse.ArgumentParser()
parser.add_argument("--add-series", help="Search string of Series name to add")
parser.add_argument("--add-eps", action="store_true",
                    help="Add new episodes")
parser.add_argument("--series-ids", nargs="*", type=int,
                    help="Limit to series_ids")
parser.add_argument("--download", action="store_true",
                    help="Add torrents and initiate tranfer, limit to only --series-ids if desired")
parser.add_argument("--status", action="store_true",
                    help="Check for any completed transfers and process them")
args = parser.parse_args()

if __name__ == "__main__":
    fetcher = EpisodeFetcher(config_fp)

    if args.add_series or args.add_eps:
        api_config = get_config_values(DEFAULTAPI)
        api = TVDBAPI(api_config)
        api.login()

    if args.add_series:
        api.search_and_add_new_series(args.add_series)
    if args.add_eps:
        api.add_series_episodes(series_ids=args.series_ids)

    if args.download:
        fetcher.download_all_non_complete_episodes(args.series_ids)
    if args.status:
        fetcher.check_downloading_torrents()

