from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from invest.core.passwords import hash_password
from invest.db.models import LoginLog, SiteUser

_PHONE_RE = re.compile(r"^1\d{10}$")


def normalize_phone(phone: str) -> str:
    value = str(phone or "").strip()
    if not _PHONE_RE.match(value):
        raise ValueError("手机号须为 11 位中国大陆号码")
    return value


class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_users(self) -> list[SiteUser]:
        return list(
            self.session.execute(
                select(SiteUser).order_by(SiteUser.id.desc())
            )
            .scalars()
            .all()
        )

    def get_user(self, user_id: int) -> SiteUser | None:
        return self.session.get(SiteUser, user_id)

    def get_by_phone(self, phone: str) -> SiteUser | None:
        return self.session.execute(
            select(SiteUser).where(SiteUser.phone == phone)
        ).scalar_one_or_none()

    def create_user(
        self,
        *,
        phone: str,
        password: str,
        display_name: str | None = None,
        enabled: bool = True,
    ) -> SiteUser:
        phone = normalize_phone(phone)
        if not password or len(password) < 6:
            raise ValueError("密码至少 6 位")
        if self.get_by_phone(phone):
            raise ValueError("手机号已存在")
        row = SiteUser(
            phone=phone,
            password_hash=hash_password(password),
            display_name=(display_name or "").strip() or None,
            enabled=enabled,
        )
        self.session.add(row)
        self.session.flush()
        return row

    def update_user(
        self,
        user_id: int,
        *,
        phone: str | None = None,
        password: str | None = None,
        display_name: str | None = None,
        enabled: bool | None = None,
    ) -> SiteUser:
        row = self.get_user(user_id)
        if not row:
            raise ValueError("用户不存在")
        if phone is not None:
            phone = normalize_phone(phone)
            existing = self.get_by_phone(phone)
            if existing and existing.id != user_id:
                raise ValueError("手机号已存在")
            row.phone = phone
        if password:
            if len(password) < 6:
                raise ValueError("密码至少 6 位")
            row.password_hash = hash_password(password)
        if display_name is not None:
            row.display_name = display_name.strip() or None
        if enabled is not None:
            row.enabled = enabled
        row.updated_at = datetime.utcnow()
        return row

    def delete_user(self, user_id: int) -> bool:
        row = self.get_user(user_id)
        if not row:
            return False
        self.session.delete(row)
        return True

    def user_to_dict(self, row: SiteUser) -> dict[str, Any]:
        return {
            "id": row.id,
            "phone": row.phone,
            "display_name": row.display_name,
            "enabled": row.enabled,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    def create_login_log(
        self,
        *,
        phone: str,
        success: bool,
        login_type: str = "frontend",
        ip: str | None = None,
        user_agent: str | None = None,
        failure_reason: str | None = None,
    ) -> LoginLog:
        row = LoginLog(
            phone=phone,
            success=success,
            login_type=login_type,
            ip=ip,
            user_agent=(user_agent or "")[:512] or None,
            failure_reason=failure_reason,
        )
        self.session.add(row)
        self.session.flush()
        return row

    def list_login_logs(self, *, limit: int = 50, offset: int = 0) -> list[LoginLog]:
        limit = max(1, min(int(limit), 200))
        offset = max(0, int(offset))
        return list(
            self.session.execute(
                select(LoginLog)
                .order_by(LoginLog.id.desc())
                .limit(limit)
                .offset(offset)
            )
            .scalars()
            .all()
        )

    def count_login_logs(self) -> int:
        return int(
            self.session.execute(select(func.count()).select_from(LoginLog)).scalar_one()
        )

    def delete_login_log(self, log_id: int) -> bool:
        row = self.session.get(LoginLog, log_id)
        if not row:
            return False
        self.session.delete(row)
        return True

    def delete_login_logs(self, log_ids: list[int]) -> int:
        if not log_ids:
            return 0
        result = self.session.execute(
            delete(LoginLog).where(LoginLog.id.in_(log_ids))
        )
        return int(result.rowcount or 0)

    def login_log_to_dict(self, row: LoginLog) -> dict[str, Any]:
        return {
            "id": row.id,
            "phone": row.phone,
            "login_type": row.login_type,
            "success": row.success,
            "ip": row.ip,
            "user_agent": row.user_agent,
            "failure_reason": row.failure_reason,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
