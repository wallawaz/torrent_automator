## Torrent Automator ##
### Manage Downloading TV Series  ###

### Requirements ###
Python >= 3.6 

### virtualenv and packages ###
Create a virtualenv 
```sh
virtualenv -p <python3dir> venv
source venv/bin/activate
```
Install PyQt5 (Required for Python `bit-torrent`)
```sh
sudo apt-get install python3-pyqt5
sudo apt-get install python3-dev
```
---
### install ###
```sh
python setup.py [install|develop]
```
#### Third-Party Tools ####
[Jackett](https://github.com/Jackett/Jackett/blob/master/README.md)

[bit-torrent](https://github.com/borzunov/bit-torrent)

#### Download and install them
```sh
bash vendor/install.sh
```

#### Start Third-Party Servers ####
```sh
bash vendor/start.sh
```
#### Stop Third-Party Servers
```sh
bash vendor/stop.sh
```

### thetvdb.com
- Pulls series metadata (seasons, number of episodes, etc).
- Registration required for api credentials.

### Jackett
- Acts as proxy server to search for torrents across a widespread of available trackers.
- Default serves on http://localhost:9117
  - Navigate to running instance and login to desired trackers.
  - Record `api_key` and configured `trackers`.
  
### Edit TorrentAutomator.config
```
[db]
uri = <path to sqlite .db file>

[thetvdb.com]
APIUSERNAME = <apiusername>
APIKEY = <apikey>
APIUNIQUEKEY = <apiuniquekey>

[jackett]
api_key = <jackett's api key (from above)>
host = 	http://localhost:9117
trackers = <comma-separated list of trackers (from above)>
torrent_directory = <path to directory to store downloaded .torrent files>
```

### Running
1. python app.py --add-series <series_name>
1. python app.py --add-eps
1. python app.py --download (CRON)
1. python app.py --status (CRON)

