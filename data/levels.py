import datetime
import sqlalchemy
from sqlalchemy import orm

from .db_session import SqlAlchemyBase


class Levels(SqlAlchemyBase):
    __tablename__ = 'levels'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    days_period = sqlalchemy.Column(sqlalchemy.Integer)
    repetition_date = sqlalchemy.Column(sqlalchemy.DateTime, nullable=True)
