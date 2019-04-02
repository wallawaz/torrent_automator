from datetime import datetime
import unittest
import os
import tempfile
from unittest.mock import patch

from config_parser import config
from models.fetcher import EpisodeFetcher
from models.jackett import Jackett
from models.db import Episode, EpisodeTorrent, Series


FILENAME_1 = "Game.of.Thrones.s01e01.WOO"
FILENAME_2 = "Game.of.Thrones.s01e01.BOO"

TORRENT_STATUS = """Name: {name}
Download speed: {ds}/s        Upload speed: {us}/s
Size: {completed} MiB/{total} MiB     Ratio: 0.0
Progress: {percent}%
"""

def create_mock_torrent_file(mock_self, mock_series_name, mock_result):
    return "/dev/null"

def mock_torrent_filename(mock_self, mock_torrent_file):
    return FILENAME_2

def mock_torrent_transfer(mock_self, mock_torrent_file, mock_series_name):
    return None

def mock_torrent_status_downloading(mock_self):
    stdout = TORRENT_STATUS.format(
        name=FILENAME_2,
        ds="10MiB",
        us="None",
        completed="28.0",
        total="140.0",
        percent="5.0",
    )
    stderr = ""
    return (stdout, stderr)

def mock_torrent_status_complete(mock_self):
    stdout = TORRENT_STATUS.format(
        name=FILENAME_2,
        ds="None",
        us="None",
        completed="140.0",
        total="140.0",
        percent="100.0",
    )
    stderr = ""
    return (stdout, stderr)


class DefaultTestCase(unittest.TestCase):

    @classmethod
    def get_test_config(cls):
        lines = [
            "[db]",
            "uri = sqlite://",
            "",
            "[thetvdb.com]",
            "ENDPOINT = https://api.thetvdb.com",
            "APIUSERNAME = username",
            "APIKEY = key",
            "APIUNIQUEKEY = unqiuekey",
            "",
            "[jackett]",
            "api_key = api_key",
            "host = http://localhost:9117",
            "trackers = input_trackers",
            "torrent_directory = /tmp/",
        ]
        return "\n".join(lines)

    @staticmethod
    def mock_search_results(search_string):
       return [
            {
                "id": 1,
                "Link": f"https://fake-torrents.com/download?file={FILENAME_1}",
                "Seeders": 83,
            },
            {
                "id": 2,
                "Link": f"https://fake-torrents.com/download?file={FILENAME_2}",
                "Seeders": 100,
            },
        ]

    def _add_series_and_episodes(cls):
        new_series = Series(
            id=1,
            name="Game of Thrones",
            air_time="9pm",
            air_days_of_week="Sun",
        )
        cls.fetcher.session.add(new_series)
        cls.fetcher.session.flush()

        new_episode = Episode(
            id=1234,
            series_id=new_series.id,
            season_number=1,
            episode_number=1,
            name="Winter is Coming",
            air_date=datetime(2011, 4, 17),
            overview=(
                "Ned Stark, Lord of Winterfell learns that his mentor, "
                "Jon Arryn, has died..."
            )
        )
        cls.fetcher.session.add(new_episode)
        cls.fetcher.session.commit()

    def _create_torrent_file(self):
        self.torrent_file = get_temporary_tf()

    def _get_episode(self):
        return (
            self.fetcher.session.query(Episode).order_by(Episode.episode_number)
        ).first()

    def setUp(self):
        self.config_str = self.get_test_config()
        self.fetcher = EpisodeFetcher(self.config_str)
        self._add_series_and_episodes()

    def tearDown(self):
        pass

    def test_episode_indexed_name(self):
        episode = self._get_episode()
        self.assertEqual(episode.indexed_name, "Game of Thrones s01e01")

    @patch.object(Jackett, "search", mock_search_results)
    def test_search_torrent(self):
        """
        Test searches results are returned in the correct order.
        """
        episode = self._get_episode()
        search_results = self.fetcher.jackett.search(episode.indexed_name)
        best_result = self.fetcher.best_search_result(search_results)
        self.assertEqual(best_result.get("id"), 2)

    @patch.object(Jackett, "search", mock_search_results)
    def test_search_torrent(self):
        """
        Test search results are returned in the correct order.
        """
        episode = self._get_episode()
        search_results = self.fetcher.jackett.search(episode.indexed_name)
        best_result = self.fetcher.best_search_result(search_results)
        self.assertEqual(best_result.get("id"), 2)

    @patch.object(Jackett, "search", mock_search_results)
    @patch.object(Jackett, "download_torrent_file", create_mock_torrent_file)
    @patch.object(EpisodeFetcher, "_binary_torrent_filename", mock_torrent_filename)
    @patch.object(Jackett, "start_torrent_transfer", mock_torrent_transfer)
    def test_download_specific_episode(self):
        """
        Test downloading an episode torrent.
        """
        episode = self._get_episode()
        torrent_filename = self.fetcher.download_specific_episode(episode)
        self.assertEqual(torrent_filename, FILENAME_2)

    @patch.object(Jackett, "search", mock_search_results)
    @patch.object(Jackett, "download_torrent_file", create_mock_torrent_file)
    @patch.object(EpisodeFetcher, "_binary_torrent_filename", mock_torrent_filename)
    @patch.object(Jackett, "start_torrent_transfer", mock_torrent_transfer)
    @patch.object(Jackett, "bittorrent_cli_status", mock_torrent_status_downloading)
    def test_check_torrent_status_downloading(self):
        """
        Test grabbing current status.
        """
        episode = self._get_episode()
        torrent_filename = self.fetcher.download_specific_episode(episode)
        self.fetcher.check_downloading_torrents()

        episode_torrent = (
            self.fetcher.session.query(EpisodeTorrent)
            .filter(EpisodeTorrent.torrent_name == torrent_filename)
        ).first()
        self.assertIsNotNone(episode_torrent)
        self.assertIsNot(episode_torrent.complete, True)

    @patch.object(Jackett, "search", mock_search_results)
    @patch.object(Jackett, "download_torrent_file", create_mock_torrent_file)
    @patch.object(EpisodeFetcher, "_binary_torrent_filename", mock_torrent_filename)
    @patch.object(Jackett, "start_torrent_transfer", mock_torrent_transfer)
    @patch.object(Jackett, "bittorrent_cli_status", mock_torrent_status_complete)
    def test_check_torrent_status_complete(self):
        """
        Test grabbing completed torrents.
        """

        episode = self._get_episode()
        torrent_filename = self.fetcher.download_specific_episode(episode)
        self.fetcher.check_downloading_torrents()

        episode_torrent = (
            self.fetcher.session.query(EpisodeTorrent)
            .filter(EpisodeTorrent.torrent_name == torrent_filename)
        ).first()
        self.assertIsNotNone(episode_torrent)
        self.assertEqual(episode_torrent.complete, True)


if __name__ == "__main__":
    unittest.main()
