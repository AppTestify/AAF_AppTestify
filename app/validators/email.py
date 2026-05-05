"""Auth email parsing: allows local bootstrap addresses (e.g. admin@localhost) that EmailStr rejects."""

from __future__ import annotations

from typing import Annotated

from pydantic import PlainValidator


def parse_auth_email(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("Email must be a string")
    s = value.strip().lower()
    if len(s) < 3 or len(s) > 255:
        raise ValueError("Invalid email address")
    if s.count("@") != 1:
        raise ValueError("Invalid email address")
    local, domain = s.split("@", 1)
    if not local or not domain:
        raise ValueError("Invalid email address")
    # email-validator (EmailStr) requires a dot in the domain; allow bare localhost for dev bootstrap
    if "." not in domain and domain != "localhost":
        raise ValueError("Invalid email address")
    return s


AuthEmail = Annotated[str, PlainValidator(parse_auth_email)]
