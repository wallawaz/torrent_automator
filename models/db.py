from datetime import datetime
import os

from sqlalchemy import (
    Column,
    create_engine,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,)

from sqlalchemy.types import Boolean, Date
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
    air_date = Column(DateTime())
    overview = Column(String)
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
    info_hash = Column(String, primary_key=True)
    episode_id = Column(Integer, ForeignKey("episode.id"))
    filename = Column(String)
    torrent_name = Column(String)
    archive_file = Column(String)
    complete = Column(Boolean, default=False)
    created_at = Column(DateTime(), default=datetime.utcnow)
    completed_at = Column(DateTime())
    episode = relationship(Episode)

Index("idx_episode_torrent_filename", EpisodeTorrent.filename)

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
