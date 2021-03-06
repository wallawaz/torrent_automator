from datetime import datetime
import json
import requests

from .db import (
    get_session,
    Episode,
    Series,
)
from exceptions import MissingSeries
from utils.config_parser import get_config_values
from utils.decorators import must_be_set

TOKEN = "jwt_token"


class TVDBAPI:
    DEFAULTAPI = "thetvdb.com"

    headers = {
        'Accept' : 'application/json',
        'Content-Type' : 'application/json',
        "Accept-Encoding": "gzip, deflate, sdch, br",
        "Accept-Language": "en-US,en;q=0.8",
        # TVDB wants curl...
        "User-Agent": "curl/7.60.0",
    }
    routes = {
        "episodes": "/series/{}/episodes",
        "search": "/search/series",
        "series": "/series/{}",
    }

    def update_headers(self):
        self.headers.update(
            Authorization="Bearer {}".format(self.jwt_token)
        )

    def _set_config_values(self):
        config_values = get_config_values(self.config, self.DEFAULTAPI)
        db_values = get_config_values(self.config, "db")
        self.base_endpoint = config_values.get("endpoint")
        self.apikey = config_values.get("apikey")
        self.session = get_session(db_values.get("uri"))

    def __init__(self, config_fp):
        self.config = config_fp
        self._set_config_values()
        self.series_map = dict()

    def login(self):
        login_endpoint = self.base_endpoint + "/login"
        data = {"apikey": self.apikey}
        response = requests.post(
            login_endpoint,
            headers=self.headers,
            json=data
        )
        content = json.loads(response.content)
        jwt_token = content.get("token")
        if not jwt_token:
            raise Exception("Login Error")
        self.jwt_token = jwt_token
        self.update_headers()

    @must_be_set(TOKEN)
    def search_for_series(self, series_name):
        search_endpoint = self.base_endpoint + self.routes["search"]
        payload = {"name": series_name}
        response = requests.get(
            search_endpoint,
            headers=self.headers,
            params=payload,
        )
        if response.status_code != 200:
            raise Exception("Invalid Request")

        content = json.loads(response.content)
        return content["data"]

    def _page_through_response(self, series_id, endpoint, response):
        content = json.loads(response.content)
        yield content.get("data")

        links = content.get("links")
        if not links or not links.get("next"):
            return
        link_next = links.get("next")
        self.series_map[series_id] = link_next

        payload = {"page": link_next}
        res = requests.get(
            endpoint,
            headers=self.headers,
            params=payload,
        )
        return self._page_through_response(series_id, endpoint, res)

    @must_be_set(TOKEN)
    def get_series_episodes(self, series):
        series_id = series.id
        series_endpoint = (
            self.base_endpoint + self.routes["episodes"].format(series_id)
        )
        payload = {}

        # If we have seen this series before and it requires paging:
        if series.pages > 0:
            payload["page"] = series.pages

        #TODO
        response = requests.get(
            series_endpoint,
            headers=self.headers,
            params=payload,
        )
        if response.status_code != 200:
            raise Exception("Invalid Request")

        return self._page_through_response(
            series_id,
            series_endpoint,
            response,
        )

    def pick_correct_series_id(self, results):
        dashes = lambda: print("-" * 80)

        def add_key_if_exists(output, key, result, truncate=False):
            val = result.get(key)
            if not val:
                return output
            if truncate:
                val = val.split(" ")[:25]
                val = " ".join(val) + "..."
            output += ', {0}: "{1}"'.format(key, val)
            return output

        output_str = 'ID: {id}, name: "{name}"'
        dashes()
        for r in results:
            output = output_str.format(
                id=r["id"],
                name=r["seriesName"]
            )
            output = add_key_if_exists(output, "network", r)
            output = add_key_if_exists(output, "firstAired", r)
            output = add_key_if_exists(output, "overview", r, truncate=True)
            print(output)
            dashes()

        msg = "Please enter the ID of the intended series: "
        msg += '\nEnter "0" if the intended series is not found: '
        _id = input(msg)
        try:
            _id = int(_id)
        except ValueError:
            raise Exception("Invalid ID. ID must be a numeric value.")
        return _id

    def add_series(self, series_dict):
        if self.session.query(Series).get(series_dict["id"]) is not None:
            print("Series {} already exists.".format(series_dict["id"]))
            return

        series_dict = dict(
            id=series_dict.get("id"),
            name=series_dict.get("seriesName"),
            air_time=series_dict.get("air_time"),
            air_days_of_week=series_dict.get("air_days_of_week"),
        )
        series = Series(**series_dict)
        self.session.add(series)
        self.session.commit()

    def search_and_add_new_series(self, search_string):
        res = self.search_for_series(search_string)
        series_id = self.pick_correct_series_id(res)
        series = None

        for r in res:
            if r["id"] == series_id:
                series = r
                break
        if series:
            self.add_series(series)

    def add_series_episodes(self, series_ids=None):
        query = self.session.query(Series)
        if series_ids:
            query = query.filter(Series.id.in_(series_ids))

        for series in query:
            # yielded lists
            for episodes in self.get_series_episodes(series):
                self._insert_episodes(series, episodes)
        self._update_series_max_page()

    def _insert_episodes(self, series, episodes):
        def get_fields(ep):

            air_date = ep.get("firstAired")
            if air_date == "":
                air_date = None
            if air_date:
                air_date = datetime.strptime(air_date, "%Y-%m-%d")
            return {
                "id": ep.get("id"),
                "series_id": ep.get("seriesId"),
                "season_number": ep.get("airedSeason"),
                "episode_number": ep.get("airedEpisodeNumber"),
                "name": ep.get("episodeName"),

                #TODO: future air_date; what is the expected key?
                "air_date": air_date,
                "overview": ep.get("overview"),
            }
        added = 0
        for ep in episodes:
            query = (
                self.session.query(Episode)
                .filter(Episode.id == ep.get("id"))
                .filter(Episode.series_id == ep.get("seriesId"))
            )
            if query.first() is None:
                new_ep = Episode(**get_fields(ep))
                self.session.add(new_ep)
                added += 1

        print('Added {} episodes for "{}"'.format(added, series.name))
        self.session.commit()

    def _update_series_max_page(self):
        """
        Long running series must be paginated through.
        Update any series contained in self.series_map.
        """
        for series_id, max_page in self.series_map.items():
            series = self.session.query(Series).get(series_id)
            series.pages = max_page
        self.session.commit()

    def view_all_series(self):
        for series in self.session.query(Series):
            print(f"{series.id}: {series.name}: Latest Episode(s)")
            query = (
                self.session.query(Episode)
                .filter(Episode.series_id == series.id)
            ).order_by(Episode.air_date.desc()).limit(3)
            for ep in query:
                print(f"{ep.episode_number} - {ep.air_date}")
            print("-" * 10)




