from __future__ import annotations

from typing import Iterable

from .errors import DuplicateError, NotFoundError, ValidationError
from .models import Instructor
from .store import Store
from .students import validate_email


def _norm(skills: Iterable[str]):
    return {s.strip().lower() for s in skills if s and s.strip()}


class InstructorService:
    def __init__(self, store: Store):
        self.s = store

    def create(self, name: str, email: str, bio: str = "", skills: Iterable[str] = ()) -> Instructor:
        if not (name or "").strip():
            raise ValidationError("name is required")
        email = validate_email(email)
        if any(i.email == email for i in self.s.instructors.values()):
            raise DuplicateError(f"instructor with email {email} already exists")
        ins = Instructor(self.s.next_id(), name.strip(), email, bio, _norm(skills))
        self.s.instructors[ins.id] = ins
        return ins

    def get(self, instructor_id: int) -> Instructor:
        try:
            return self.s.instructors[instructor_id]
        except KeyError:
            raise NotFoundError(f"instructor {instructor_id} not found")

    def add_skills(self, instructor_id: int, skills: Iterable[str]) -> Instructor:
        ins = self.get(instructor_id)
        ins.skills |= _norm(skills)
        return ins

    def remove_skill(self, instructor_id: int, skill: str) -> Instructor:
        ins = self.get(instructor_id)
        ins.skills.discard(skill.strip().lower())
        return ins

    def find_by_skill(self, skill: str):
        skill = skill.strip().lower()
        return sorted((i for i in self.s.instructors.values() if skill in i.skills), key=lambda i: i.id)

    def courses_of(self, instructor_id: int):
        self.get(instructor_id)
        return sorted((c for c in self.s.courses.values() if c.instructor_id == instructor_id),
                      key=lambda c: c.id)

    def assign_course(self, instructor_id: int, course_id: int):
        self.get(instructor_id)
        try:
            course = self.s.courses[course_id]
        except KeyError:
            raise NotFoundError(f"course {course_id} not found")
        course.instructor_id = instructor_id
        return course

    def unassign_course(self, course_id: int):
        try:
            course = self.s.courses[course_id]
        except KeyError:
            raise NotFoundError(f"course {course_id} not found")
        course.instructor_id = None
        return course
