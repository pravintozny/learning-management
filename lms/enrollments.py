from __future__ import annotations

from typing import List, Optional

from .courses import CourseService
from .errors import EnrollmentError, NotFoundError, PrerequisiteError
from .models import DROPPED, ENROLLED, Enrollment, HistoryEvent
from .store import Store


class EnrollmentService:
    def __init__(self, store: Store, courses: CourseService):
        self.s = store
        self.courses = courses

    def active_count(self, course_id: int) -> int:
        return sum(1 for e in self.s.enrollments.values()
                   if e.course_id == course_id and e.status == ENROLLED)

    def seats_left(self, course_id: int) -> Optional[int]:
        cap = self.courses.get(course_id).capacity
        return None if cap is None else max(0, cap - self.active_count(course_id))

    def find(self, student_id: int, course_id: int, status: Optional[str] = None) -> Optional[Enrollment]:
        matches = [e for e in self.s.enrollments.values()
                   if e.student_id == student_id and e.course_id == course_id
                   and (status is None or e.status == status)]
        return max(matches, key=lambda e: e.id) if matches else None

    def enroll(self, student_id: int, course_id: int) -> Enrollment:
        if student_id not in self.s.students:
            raise NotFoundError(f"student {student_id} not found")
        course = self.courses.get(course_id)
        existing = self.find(student_id, course_id)
        if existing and existing.status == ENROLLED:
            raise EnrollmentError("student is already enrolled in this course")
        if existing and existing.status == "completed":
            raise EnrollmentError("student has already completed this course")
        missing = self.courses.missing_prerequisites(student_id, course_id)
        if missing:
            raise PrerequisiteError(f"missing completed prerequisites: {missing}")
        if course.capacity is not None and self.active_count(course_id) >= course.capacity:
            raise EnrollmentError("course is at capacity")
        e = Enrollment(self.s.next_id(), student_id, course_id, ENROLLED, self.s.clock())
        self.s.enrollments[e.id] = e
        self.s.history.append(HistoryEvent(e.enrolled_at, student_id, course_id, "enrolled", course.title))
        return e

    def drop(self, student_id: int, course_id: int) -> Enrollment:
        e = self.find(student_id, course_id, ENROLLED)
        if not e:
            raise EnrollmentError("no active enrollment to drop")
        e.status = DROPPED
        e.dropped_at = self.s.clock()
        self.s.history.append(HistoryEvent(e.dropped_at, student_id, course_id, "dropped"))
        return e

    def for_course(self, course_id: int, status: Optional[str] = None) -> List[Enrollment]:
        self.courses.get(course_id)
        return sorted((e for e in self.s.enrollments.values()
                       if e.course_id == course_id and (status is None or e.status == status)),
                      key=lambda e: e.id)
