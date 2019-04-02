import os

from sqlalchemy import create_engine, Column, ForeignKey, Integer, String
from sqlalchemy.types import Boolean, Date
from sqlalchemy.dialects.sqlite import TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()


class Series(Base):
    __tablename__ = "series"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    air_time = Column(String)
    air_days_of_week = Column(String)
    pages = Column(Integer, default=0)


class Episode(Base):
    __tablename__ = "episode"

    series_id = Column(Integer, ForeignKey("series.id"), primary_key=True)
    id = Column(Integer, primary_key=True)
    season_number = Column(Integer)
    episode_number = Column(Integer)
    name = Column(String)
    air_date = Column(Date)
    overview = Column(String)
    #downloaded = Column(Boolean, default=False)
    series = relationship(Series)

    @property
    def indexed_name(self):
        season = str(self.season_number).zfill(2)
        episode_number = str(self.episode_number).zfill(2)
        indexed_name = "{name} s{s}e{e}".format(
            name=self.series.name,
            s=season,
            e=episode_number,
        )
        return indexed_name

class EpisodeTorrent(Base):
    __tablename__ = "episode_torrent"
    id = Column(Integer, autoincrement=True, primary_key=True)
    episode_id = Column(Integer, ForeignKey("episode.id"))
    torrent_name = Column(String)
    archive_file = Column(String)
    complete = Column(Boolean, default=False)
    completed_at = Column(TIMESTAMP)
    info_hash = Column(String)
    episode = relationship(Episode)

#def _get_db_path():
#    return os.path.join(
#        os.path.abspath(__file__ + "/../../"),
#        "data",
#        "series.db"
#    )

#def _get_engine_uri(driver):
#    db_path = _get_db_path()
#    engine_uri = EngineMap.get(driver)
#    if not engine_uri:
#        raise Exception("Engine Type not implemented")
#    return engine_uri.format(db_path)

def get_engine(db_uri):
    """Creates the db engine"""

    engine = create_engine(db_uri)
    in_memory = not db_uri.endswith(".db") or db_uri.endswith(".sqlite")
    if in_memory:
        Base.metadata.create_all(engine)
        return engine

    #TODO fix for other db uris.
    db_path = db_uri[9:]
    if not os.path.exists(db_path):
        Base.metadata.create_all(engine)
    return engine

def get_session(db_uri):
    engine = get_engine(db_uri)
    Base.metadata.bind = engine
    DBSession = sessionmaker(bind=engine)
    return DBSession()
