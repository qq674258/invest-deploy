from __future__ import annotations

import logging
import re
import smtplib
from email import policy
from email.header import Header
from email.message import EmailMessage
from email.utils import formataddr, parseaddr
from typing import Any

from invest.core.alert_config import effective_smtp_password

logger = logging.getLogger(__name__)

_ASCII_EMAIL_RE = re.compile(r"^[^@\s<>]+@[^@\s<>]+\.[^@\s<>]+$")


def _ascii_email_only(addr: str, *, label: str) -> str:
    """Extract bare ASCII mailbox for SMTP envelope (MAIL FROM / RCPT TO)."""
    _, email = parseaddr(addr.strip())
    mailbox = (email or "").strip()
    if not mailbox:
        raise ValueError(f"{label}请填写有效邮箱地址")
    try:
        mailbox.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError(
            f"{label}请使用英文邮箱地址；若需中文昵称，请用「昵称 <邮箱>」格式"
        ) from exc
    if not _ASCII_EMAIL_RE.match(mailbox):
        raise ValueError(f"{label}格式无效：{mailbox}")
    return mailbox


def _format_mailbox_header(addr: str, mailbox: str) -> str:
    """Encode optional display name; keep mailbox ASCII for compatibility."""
    name, parsed = parseaddr(addr.strip())
    use_mailbox = (parsed or mailbox).strip()
    if name:
        return formataddr((Header(name, "utf-8").encode(), use_mailbox))
    return use_mailbox


def _format_subject(subject: str) -> str:
    return Header(subject, "utf-8").encode()


def send_email(
    cfg: dict[str, Any],
    *,
    subject: str,
    body: str,
) -> None:
    email = cfg.get("email") or {}
    if not email.get("enabled"):
        raise ValueError("邮件未启用")
    host = str(email.get("smtp_host") or "").strip()
    port = int(email.get("smtp_port") or 465)
    user = str(email.get("smtp_user") or "").strip()
    password = effective_smtp_password(cfg)
    from_addr = str(email.get("from_addr") or user).strip()
    to_addrs = [str(x).strip() for x in (email.get("to_addrs") or []) if str(x).strip()]
    if not host or not from_addr or not to_addrs:
        raise ValueError("请填写 SMTP 服务器、发件人与收件人")

    envelope_from = _ascii_email_only(from_addr or user, label="发件人")
    envelope_to = [_ascii_email_only(addr, label="收件人") for addr in to_addrs]

    msg = EmailMessage(policy=policy.SMTP)
    msg["Subject"] = _format_subject(subject)
    msg["From"] = _format_mailbox_header(from_addr or user, envelope_from)
    msg["To"] = ", ".join(
        _format_mailbox_header(addr, mailbox)
        for addr, mailbox in zip(to_addrs, envelope_to, strict=True)
    )
    msg.set_content(body, charset="utf-8")
    payload = msg.as_bytes()

    use_ssl = bool(email.get("smtp_use_ssl", True))
    logger.info("发送邮件至 %s via %s:%s", envelope_to, host, port)
    if use_ssl:
        with smtplib.SMTP_SSL(host, port, timeout=30) as smtp:
            if user:
                smtp.login(user, password)
            smtp.sendmail(envelope_from, envelope_to, payload)
    else:
        with smtplib.SMTP(host, port, timeout=30) as smtp:
            smtp.ehlo()
            smtp.starttls()
            if user:
                smtp.login(user, password)
            smtp.sendmail(envelope_from, envelope_to, payload)
