import sqlalchemy
from .db_session import SqlAlchemyBase


class Cards(SqlAlchemyBase):
    __tablename__ = 'cards'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    front_side = sqlalchemy.Column(sqlalchemy.String)
    back_side = sqlalchemy.Column(sqlalchemy.String)
    level = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("levels.id"))
    repetition_date = sqlalchemy.Column(sqlalchemy.DateTime, nullable=True)

