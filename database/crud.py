import re
from typing import List, Optional
from unittest import result

from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select

from database.models import District, User


async def get_or_create_user(db, telegram_id: int, **kwargs) -> User:
    """
    Получает пользователя по telegram_id или создает нового, если не существует
    """
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()

    if not user:
        user = User(telegram_id=telegram_id, **kwargs)
        db.add(user)
        try:
            await db.commit()
            await db.refresh(user)
        except Exception:
            await db.rollback()
            raise
    else:
        # Обновляем информацию о пользователе, если она изменилась
        updated = False
        for field in ("username", "first_name", "last_name"):
            if kwargs.get(field) is None:
                continue
            if getattr(user, field) != kwargs[field]:
                setattr(user, field, kwargs[field])
                updated = True

        if updated:
            try:
                await db.commit()
                await db.refresh(user)
            except Exception as e:
                await db.rollback()
                raise

    return user


async def get_users(db, active: Optional[bool] = None) -> List[User]:
    user_select = select(User)
    if active is not None:
        user_select = user_select.where(User.active == active)
    result = await db.execute(user_select)
    return result.scalars().all()


async def get_or_create_district(db, name: str) -> District:
    """
    Создает новый район
    """
    lower_name = name.lower()
    result = await db.execute(select(District).where(District.name == lower_name))
    district = result.scalar_one_or_none()

    if not district:
        district = District(name=lower_name)
        db.add(district)
        try:
            await db.commit()
            await db.refresh(district)
        except IntegrityError:
            await db.rollback()
            result = await db.execute(
                select(District).where(District.name == lower_name)
            )
            district = result.scalar_one_or_none()

    return district


async def get_all_districts(db) -> List[District]:
    result = await db.execute(select(District))
    return result.scalars().all()


async def get_active_users_by_district_name(db, district_names: int) -> List[User]:
    """
    Получает активных пользователей, которые подписаны на районы
    """
    district_names = district_names.lower()

    user_ids = set()
    districts = await get_all_districts(db)
    for district in districts:
        if district.name in district_names:
            await db.refresh(district, ["users"])
            for user in district.users:
                user_ids.add(user.id)

    if user_ids:
        result = await db.execute(
            select(User).where(and_(User.id.in_(user_ids), User.active == True))
        )
        return result.scalars().all()
    return []


async def add_user_to_district(db, user: User, district_name: str) -> bool:
    """
    Добавляет пользователя в район
    """
    lower_district_name = district_name.lower()
    district = await get_or_create_district(db, lower_district_name)

    await db.refresh(user, ["districts"])

    # Проверяем, не добавлен ли уже этот район пользователю
    if district not in user.districts:
        user.districts.append(district)
        try:
            await db.commit()
            return True
        except Exception:
            await db.rollback()
            return False

    return False


async def remove_district_from_user(db, user: User, district_name: str) -> bool:
    lower_district_name = district_name.lower()
    result = await db.execute(
        select(District).where(District.name == lower_district_name)
    )
    district = result.scalar_one_or_none()
    if not district:
        return False

    await db.refresh(user, ["districts"])

    if district in user.districts:
        user.districts.remove(district)
        try:
            await db.commit()
            return True
        except Exception:
            await db.rollback()
            return False

    return False


async def set_user_status(
    db, user: User, requested_activation: bool, active: bool
) -> bool:
    """
    Устанавливает статус активности пользователя
    """
    user.requested_activation = requested_activation
    user.active = active
    try:
        await db.commit()
        await db.refresh(user)
        return True
    except Exception as e:
        raise e
        await db.rollback()
        return False
