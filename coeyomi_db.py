from discord import Member
from dogpile.cache import make_region
from sqlalchemy import Column, Float, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session


class SQL:
    def __init__(self, database):
        self.Engine = create_engine(database, echo=False)
        self.Base = declarative_base()
        self.session = Session(autocommit=False, autoflush=True, bind=self.Engine)

        class User(self.Base):
            __tablename__ = "users"
            __table_args__ = {"comment": "ユーザーごとの設定(サーバー単位)"}
            server = Column("server", Integer, primary_key=True)
            user = Column("user", Integer, primary_key=True)
            style = Column("style", Integer)
            character = Column("character", String)
            pitchScale = Column("pitchScale", Float)
            intonationScale = Column("intonationScale", Float)
            processingAlgorithm = Column("processingAlgorithm", String)

        class Dict(self.Base):
            __tablename__ = "dicts"
            __table_args__ = {"comment": "サーバーごとの辞書"}
            server = Column("server", Integer, primary_key=True)
            word = Column("word", String, primary_key=True)
            yomi = Column("yomi", String)
            accent = Column("accent", Integer)

        self.User = User
        self.Dict = Dict

    region = make_region().configure("dogpile.cache.memory", expiration_time=3600)

    def createTable(self):
        self.Base.metadata.create_all(bind=self.Engine)

    @region.cache_on_arguments()
    def getUserSettings(self, user:Member,optional_guild_id:int=None):
        user_table = (
            self.session.query(self.User)
            .filter(self.User.server == (optional_guild_id or user.guild.id), self.User.user == user.id)
            .first()
        )
        if user_table is None:
            user_table = self.User()
            user_table.server = user.guild.id
            user_table.user = user.id
            self.session.add(user_table)
            self.session.commit()
        return user_table

    @region.cache_on_arguments()
    def isExistSettings(self, user:Member,optional_guild_id:int=None):
        user_table = (
            self.session.query(self.User)
            .filter(self.User.server == (optional_guild_id or user.guild.id), self.User.user == user.id)
            .first()
        )
        print(user_table is not None)
        return user_table is not None

    @region.cache_on_arguments()
    def getDictSettings(self, user:Member,word:str,optional_guild_id:int=None):
        dict_table = (
            self.session.query(self.Dict)
            .filter(self.Dict.server == (optional_guild_id or user.guild.id), self.Dict.word == word)
            .first()
        )
        if dict_table is None:
            dict_table = self.Dict()
            dict_table.server = user.guild.id
            dict_table.word = word
            self.session.add(dict_table)
            self.session.commit()
        return dict_table
