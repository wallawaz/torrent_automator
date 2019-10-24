from datetime import datetime, timedelta
import os
import re
import subprocess
import sys
import time

from sqlalchemy import and_, not_, or_
from string import digits

from .db import (
    get_session,
    Episode,
	EpisodeTorrent,
    Series,
    SeriesExclusion,
)
from .jackett import Jackett
from utils.config_parser import get_config_values
from utils.decorators import must_be_set

class EpisodeFetcher:

    def _get_jackett(self):
        jackett_config = get_config_values(self.config, "jackett")
        return Jackett(jackett_config)

    def _get_session(self):
        db_config = get_config_values(self.config, "db")
        return get_session(db_config["uri"])

    def __init__(self, config, shortened_searches=False):
        self.config = config
        self.shortened_searches = shortened_searches
        self.session = self._get_session()
        self.jackett = self._get_jackett()

    def non_downloaded_episodes(self, series_ids=[]):
        completed_cte = (
            self.session.query(EpisodeTorrent.episode_id.label("episode_id"))
            .filter(EpisodeTorrent.complete)
            .group_by(EpisodeTorrent.episode_id)
        ).cte("completed_cte")

        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        recently_added_cte = (
            self.session.query(EpisodeTorrent.episode_id.label("episode_id"))
            .filter(EpisodeTorrent.created_at >= one_hour_ago)
            .group_by(EpisodeTorrent.episode_id)
        ).cte("recently_added_cte")

        is_null_clause = and_(
            completed_cte.c.episode_id.is_(None),
            recently_added_cte.c.episode_id.is_(None),
        )
        query = (
			self.session.query(Episode)
			.outerjoin(completed_cte, completed_cte.c.episode_id == Episode.id)
            .outerjoin(recently_added_cte, recently_added_cte.c.episode_id == Episode.id)
            .outerjoin(SeriesExclusion, Episode.series_id ==
                       SeriesExclusion.series_id)
			.filter(is_null_clause)
            .filter(or_(
                SeriesExclusion.series_id.is_(None),
                Episode.air_date > SeriesExclusion.aired_after)
            )
		)
        if series_ids:
            query = query.filter(Episode.series_id.in_(series_ids))
        return query

    def _start_transfer(self, torrent_file, series_name):
        series_folder = self.jackett._series_folder(series_name)
        self.jackett.start_torrent_transfer(torrent_file, series_folder)

    def _best_result(self, search_results, excluded):
        best_result = None
        for search in search_results:
            search_filename = self.jackett.get_torrent_file_from_search(search)
            if search_filename in excluded:
                continue
            already_downloaded = (
                self.session.query(EpisodeTorrent)
                .filter(EpisodeTorrent.filename == search_filename)
            ).first()
            if already_downloaded:
                continue
            best_result = search
            best_result["filename"] = search_filename
            break
        return best_result

    @property
    def excluded_filenames(self):
        query = (
            self.session.query(SeriesExclusion.filename)
            .filter(not_(SeriesExclusion.filename.is_(None)))
        )
        return [filename for filename in query]

    def search(self, ep):
        queries = [ep.indexed_name]
        if self.shortened_searches:
            queries.append(ep.shortened_indexed_name(episode="z_episode_number"))

        for search_query in queries:
            print (f"Attempting to find torrents for: {search_query}")
            search_results = self.jackett.search(search_query)
            #print(search_results)
            if search_results:
                return search_results
        return []

    def download_all_non_complete_episodes(self, series_ids=[],
                                           pause_transfer=False):
        self._append_path()
        excluded = self.excluded_filenames
        for ep in self.non_downloaded_episodes(series_ids=series_ids):
            search_results = self.search(ep)
            if not search_results:
                continue

            search_results = self.sort_search_results(search_results)
            best_result = self._best_result(search_results, excluded)
            if not best_result:
                continue
            torrent_file = self.jackett.download_torrent_file(ep.series.name,
                                                              best_result)
            torrent_info = self._torrent_info(torrent_file)
            episode_torrent = EpisodeTorrent(
                episode_id=ep.id,
                filename=best_result["filename"],
                torrent_name=torrent_info["suggested_name"],
                archive_file=torrent_info["archive_file"],
                info_hash=torrent_info["info_hash"],
            )
            self.session.add(episode_torrent)
            self.session.commit()

            print(f"Downloaded: {ep.indexed_name}: {torrent_info['suggested_name']}")
            if pause_transfer is True:
                continue
            self._start_transfer(torrent_file, ep.series.name)
            time.sleep(15)

    def download_specific_episode(self, episode, pause=False):
        search_results = self.search(episode)
        if not search_results:
            return
        series_name = episode.series.name
        search_results = self.sort_search_results(search_results)
        torrent_file = self.jackett.download_torrent_file(series_name,
                                                          best_result)
        torrent_info = self._torrent_info(torrent_file)

        episode_torrent = EpisodeTorrent(
            episode_id=episode.id,
            torrent_name=torrent_info["suggested_name"],
            archive_file=torrent_info["archive_file"],
            info_hash=torrent_info["info_hash"],
        )
        self._start_transfer(torrent_file, series_name)
        self.session.add(episode_torrent)
        self.session.commit()
        if pause:
            #XXX wut
            import time
            time.sleep(10)
            self.jackett.pause_torrent_transfer(torrent_file)
        return torrent_name


    def current_active_episode_torrents(self):
        query = (
            self.session.query(EpisodeTorrent)
            .filter(not_(EpisodeTorrent.complete))
        )
        return query

    def check_downloading_torrents(self):
        """
        Hit the bittorrent cli for status and get results
        for all active torrents.
        """
        status_stdout, status_stderr = self.jackett.bittorrent_cli_status()
        statuses = self.parse_status_string(status_stdout)

        for ep_torrent in self.current_active_episode_torrents():
            for status in statuses:
                if ep_torrent.info_hash == status["ID"]:
                    self.process_running_torrent(ep_torrent, status)

    def sort_search_results(self, search_results):
        return sorted(search_results, key=lambda x: x["Seeders"], reverse=True)

    def _process_status_line(self, line, current_status, statuses):
        _digits = lambda x: re.findall(r'[\d\.]+', x)[0]
        P = "Progress"

        line_dict = {
            line.split(":")[0]: line.split(":")[1].strip()
        }
        if P in line_dict:
            # Convert to number
            line_dict[P] = _digits(line_dict[P])

        # Matching keys, update current_status's
        if not current_status.keys().isdisjoint(line_dict.keys()):
            current_status.update(line_dict)

        # Final line in the `status`.
        if P in line_dict:
            statuses.append(current_status)
            current_status = current_status.fromkeys(current_status)

        return (current_status, statuses)

    def parse_status_string(self, status_string):
        if isinstance(status_string, bytes):
            status_string = status_string.decode()

        statuses = []
        status_keys = [
            "Name",
            "ID",
            "State",
            "Progress",
        ]
        current_status = dict.fromkeys(status_keys)
        for line in status_string.split("\n"):
            if len(line) < 2:
                continue
            current_status, statuses = self._process_status_line(
                line,
                current_status,
                statuses
            )

        return statuses

    def process_running_torrent(self, episode_torrent, status):
        # Torrent not complete. Nothing to do.
        if float(status["Progress"]) < 100:
            print("Not complete:", status)
            return
        episode_torrent.complete = True
        episode_torrent.completed_at = datetime.utcnow()
        self.session.commit()

        if episode_torrent.archive_file:
            self.extract_archive(episode_torrent)

    def extract_archive(self, episode_torrent):
        """
        Extract the completed episode_torrent
        Using subprocess 7zip.
        """
        series_folder = (
            self.jackett._series_folder(episode_torrent.episode.series.name)
        )
        archive_path = os.path.join(
            series_folder,
            episode_torrent.archive_file,
        )
        stdout, stderr = self._7zip_subprocess(archive_path, series_folder)
        if stderr:
            print(f"Error Extracting {episode_torrent.archive_file}")
            print(stderr.decode())

    def _7zip_subprocess(self, archive_path, output_folder):
        # 7z is dumb no space
        output_switch = "-o" + output_folder
        Popen_args = [
            "7z",
            "x",
            archive_path,
            output_switch,
        ]
        _7zip_process = subprocess.Popen(Popen_args,
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE)
        stdout, stderr = _7zip_process.communicate()
        return (stdout, stderr)

    @must_be_set("path_appended")
    def _torrent_info(self, torrent_filename, download_dir=None):
        from torrent_client.models import TorrentInfo
        torrent_info = TorrentInfo.from_file(torrent_filename,
                                             download_dir=download_dir)

        torrent_info = torrent_info.download_info
        return {
            "suggested_name": torrent_info.suggested_name,
            "archive_file": self._check_archive(torrent_info.file_tree),
            "info_hash": torrent_info.info_hash.hex(),
        }

    def _check_archive(self, file_tree):
        def _min_part(min_file, min_part, filename):
            requires = ["rar", "zip", "7z"]
            filetype = filename.split(".")[-1].lower()
            if filetype in requires:
                return (filename, -1)

            fn = "".join([f for f in filetype if f in digits])
            if fn:
                fn = int(fn)
                if min_file is None or fn < min_part:
                    min_file = filename
                    min_part = fn
            return (min_file, min_part)

        min_file = None
        min_part = None
        for filename in file_tree.keys():
            min_file, min_part = _min_part(min_file, min_part, filename)
            if min_part is not None and min_part < 0:
                return filename

        return min_file

    def _append_path(self):
        sys.path.append(
            os.path.join(
                os.path.split(os.path.abspath(__file__))[0],
                "..",
                "vendor",
                "bit-torrent",
            )
        )
        self.path_appended = True
