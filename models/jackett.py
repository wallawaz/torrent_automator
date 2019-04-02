import json
import os
import requests
import subprocess
import time
from urllib.parse import parse_qs

class Jackett:
    headers = {
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'en-US,en;q=0.9',
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.121 Safari/537.36',
        'Accept': "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    }

    @property
    def search_url(self):
        return self.host + "/api/v2.0/indexers/all/results"

    def set_config_value(self, value):
        setattr(self, value, self.config[value])

    def set_config_values(self):
        for c in ["api_key", "host", "torrent_directory"]:
            self.set_config_value(c)

        # Set self.trackers as a list.
        self.trackers = self.config["trackers"].split(",")


    def __init__(self, config_section):
        self.config = config_section
        self.set_config_values()

    def search(self, search_str):
        """Search Jackett server (most likely running locally) """
        trackers = ",".join(self.trackers)

        response = requests.get(
            self.search_url,
            params={
                "Query": search_str,
                "Tracker[]": trackers,
                "apikey": self.api_key,
            }
        )
        if response.status_code != 200:
            raise Exception(response.reason)
        return json.loads(response.content)["Results"]

    def _series_folder(self, series_name):
        return os.path.join(
            self.torrent_directory,
            series_name
        )

    def output_torrent_file(self, series_name, filename):
        series_folder = self._series_folder(series_name)
        if not os.path.exists(series_folder):
            os.mkdir(series_folder)

        filename = "_".join(filename.split())
        return os.path.join(
            series_folder,
            filename + ".torrent"
        )

    def download_torrent_file(self, series_name, search_result, link="Link"):
        torrent_filename = self.get_torrent_file_from_search(
            search_result,
            link
        )
        out_torrent_file = self.output_torrent_file(series_name, torrent_filename)
        with open(out_torrent_file,  "wb") as outf:
            response = requests.get(search_result["Link"], headers=self.headers)
            outf.write(response.content)
        return out_torrent_file

    def get_torrent_file_from_search(self, search_result, link):
        try:
            url = search_result[link]
            parsed_url = parse_qs(url)
            filename = parsed_url["file"]
        except KeyError:
            raise SearchResultMissingFile
        return filename[0]

    @property
    def python3path(self):
        return os.path.join(
            os.path.abspath(__file__ + "/../../"),
            "venv",
            "bin",
            "python3"
        )

    @property
    def bittorrent_cli(self):
        return os.path.join(
            os.path.abspath(__file__ + "/../../"),
            "vendor",
            "bit-torrent",
            "torrent_cli.py"
        )

    def bittorrent_cli_status(self):
        Popen_args = [
            self.python3path,
            self.bittorrent_cli,
            "status",
            "-v",
        ]
        status_process = subprocess.Popen(Popen_args,
                                          stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE)
        stdout, stderr = status_process.communicate()
        return (stdout, stderr)

    def start_torrent_transfer(self, torrent_file, download_directory):
        Popen_args = [
            self.python3path,
            self.bittorrent_cli,
            "add",
            torrent_file,
            "-d",
            download_directory,
        ]
        start_torrent_process = subprocess.Popen(Popen_args,
                                                 stdout=subprocess.PIPE,
                                                 stderr=subprocess.PIPE)
        stdout, stderr = start_torrent_process.communicate()
        if bool(stderr.decode()):
            raise Exception("Error initiating torrent transfer: "
                            "{}".format(stderr.decode()))

    def pause_torrent_transfer(self, torrent_file):
        Popen_args = [
            self.python3path,
            self.bittorrent_cli,
            "pause",
            torrent_file,
        ]
        pause_torrent_process = subprocess.Popen(Popen_args,
                                                 stdout=subprocess.PIPE,
                                                 stderr=subprocess.PIPE)
        stdout, stderr = pause_torrent_transfer.communicate()
        if bool(stderr.decode()):
            raise Exception("Error pausing torrent {}".format(stderr.decode()))
