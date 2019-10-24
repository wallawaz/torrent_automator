import argparse
import sys

from models.fetcher import EpisodeFetcher
from models.tvdb import TVDBAPI


config_fp = "config.ini"

parser = argparse.ArgumentParser()
parser.add_argument("--add-series", help="Search string of Series name to add")
parser.add_argument("--add-eps", action="store_true",
                    help="Add new episodes")
parser.add_argument("--series-ids", nargs="*", type=int,
                    help="Limit to series_ids")
parser.add_argument("--download", action="store_true",
                    help="Add torrents and initiate tranfer, limit to only --series-ids if desired")
parser.add_argument("--pause-transfer", action="store_true",
                    help="Do not immediately start torrent transfers")
parser.add_argument("--status", action="store_true",
                    help="Check for any completed transfers and process them")
parser.add_argument("--view-series", help="View added series info",
                    action="store_true")
parser.add_argument(
    "--shortened-searches",
    help="Search for episodes using a shortened episode name",
    action="store_true",
)


args = parser.parse_args()

if __name__ == "__main__":
    fetcher = EpisodeFetcher(
        config_fp,
        shortened_searches=args.shortened_searches
    )
    if args.view_series:
        api = TVDBAPI(config_fp)
        api.view_all_series()
        sys.exit(0)

    if args.series_ids is None:
        series_ids = []

    if args.add_series or args.add_eps:
        api = TVDBAPI(config_fp)
        api.login()

    if args.add_series:
        api.search_and_add_new_series(args.add_series)
    if args.add_eps:
        api.add_series_episodes(series_ids=args.series_ids)

    if args.download:
        fetcher.download_all_non_complete_episodes(
            series_ids=args.series_ids,
            pause_transfer=args.pause_transfer
        )
    if args.status:
        fetcher.check_downloading_torrents()

