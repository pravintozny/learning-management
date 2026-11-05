from __future__ import annotations

import re

from .errors import DuplicateError, NotFoundError, ValidationError
from .models import HistoryEvent, Student
from .store import Store

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_email(email: str) -> str:
    email = (email or "").strip().lower()
    if not _EMAIL.match(email):
        raise ValidationError(f"invalid email: {email!r}")
    return email


class StudentService:
    def __init__(self, store: Store):
        self.s = store

    def register(self, name: str, email: str, bio: str = "") -> Student:
        if not (name or "").strip():
            raise ValidationError("name is required")
        email = validate_email(email)
        if any(st.email == email for st in self.s.students.values()):
            raise DuplicateError(f"student with email {email} already registered")
        st = Student(self.s.next_id(), name.strip(), email, self.s.clock(), bio)
        self.s.students[st.id] = st
        self.s.history.append(
            HistoryEvent(
                st.registered_at, st.id, None, "registered", name.strip()))
        return st

    def get(self, student_id: int) -> Student:
        try:
            return self.s.students[student_id]
        except KeyError:
            raise NotFoundError(f"student {student_id} not found")

    def update_profile(self, student_id: int, name=None, email=None, bio=None) -> Student:
        st = self.get(student_id)
        if name is not None:
            if not name.strip():
                raise ValidationError("name is required")
            st.name = name.strip()
        if email is not None:
            email = validate_email(email)
            if any(o.email == email and o.id != st.id for o in self.s.students.values()):
                raise DuplicateError(f"email {email} already in use")
            st.email = email
        if bio is not None:
            st.bio = bio
        return st

    def list(self):
        return sorted(self.s.students.values(), key=lambda x: x.id)

    def enrollment_history(self, student_id: int):
        self.get(student_id)
        return sorted((e for e in self.s.enrollments.values() if e.student_id == student_id),
                      key=lambda e: (e.enrolled_at, e.id))
