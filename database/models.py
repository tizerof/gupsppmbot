import datetime as dt

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
)
from sqlalchemy.orm import relationship

from database import Base

user_district = Table(
    "user_district",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("district_id", Integer, ForeignKey("districts.id"), primary_key=True),
)


class User(Base):
    """
    Модель пользователя Telegram
    """

    __tablename__ = "users"

    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)

    created_at = Column(DateTime, default=dt.datetime.now, nullable=False)
    requested_activation = Column(Boolean, default=False)
    active = Column(Boolean, default=False)

    districts = relationship(
        "District", secondary=user_district, back_populates="users"
    )

    @property
    def full_name(self):
        """Получить полное имя пользователя"""
        full_name = ""
        if self.first_name:
            full_name += f"{self.first_name} "
        if self.last_name:
            full_name += f"{self.last_name} "
        return full_name.strip()

    @property
    def tg_link(self):
        user_name = self.full_name or self.username or self.telegram_id
        return f"<a href='tg://user?id={self.telegram_id}'>{user_name}</a>"

    def add_district(self, district):
        """Добавить район пользователю"""
        if district not in self.districts:
            self.districts.append(district)

    def remove_district(self, district):
        """Удалить район у пользователя"""
        if district in self.districts:
            self.districts.remove(district)

    def has_district(self, district):
        """Проверить, есть ли у пользователя данный район"""
        return district in self.districts

    def get_district_names(self):
        """Получить список названий районов пользователя"""
        return [district.name for district in self.districts]

    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username='{self.username}')>"


class District(Base):
    """
    Модель района
    """

    __tablename__ = "districts"

    name = Column(String, unique=True, index=True, nullable=False)

    users = relationship("User", secondary=user_district, back_populates="districts")

    def add_user(self, user):
        """Добавить пользователя в район"""
        if user not in self.users:
            self.users.append(user)

    def remove_user(self, user):
        """Удалить пользователя из района"""
        if user in self.users:
            self.users.remove(user)

    def has_user(self, user):
        """Проверить, есть ли пользователь в данном районе"""
        return user in self.users

    def get_user_count(self):
        """Получить количество пользователей в районе"""
        return len(self.users)

    def __repr__(self):
        return f"<District(id={self.id}, name='{self.name}')>"
