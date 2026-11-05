from __future__ import annotations

from typing import List
from uuid import uuid4

from .courses import CourseService
from .enrollments import EnrollmentService
from .errors import EnrollmentError, NotFoundError, ValidationError
from .grading import GradingService
from .models import COMPLETED, ENROLLED, Certificate, HistoryEvent
from .store import Store


class ProgressService:
    def __init__(self, store: Store, courses: CourseService,
                 enrollments: EnrollmentService, grading: GradingService):
        self.s = store
        self.courses = courses
        self.enrollments = enrollments
        self.grading = grading

    def complete_lesson(self, student_id: int, course_id: int, lesson_id: int) -> float:
        """Marks a lesson complete (idempotent); returns completion percentage."""
        course = self.courses.get(course_id)
        if not self.enrollments.find(student_id, course_id, ENROLLED):
            raise EnrollmentError("student is not actively enrolled in this course")
        if lesson_id not in {l.id for l in course.lessons()}:
            raise NotFoundError(f"lesson {lesson_id} not in course {course_id}")
        done = self.s.completed_lessons.setdefault((student_id, course_id), set())
        if lesson_id not in done:
            done.add(lesson_id)
            title = next(l.title for l in course.lessons() if l.id == lesson_id)
            self.s.history.append(HistoryEvent(self.s.clock(), student_id, course_id,
                                               "lesson_completed", title))
        return self.completion_percentage(student_id, course_id)

    def completion_percentage(self, student_id: int, course_id: int) -> float:
        total = len(self.courses.get(course_id).lessons())
        if total == 0:
            return 0.0
        done = self.s.completed_lessons.get((student_id, course_id), set())
        return round(100.0 * len(done) / total, 2)

    def can_complete(self, student_id: int, course_id: int) -> bool:
        return (self.completion_percentage(student_id, course_id) >= 100.0
                and self.grading.is_passing(student_id, course_id))

    def complete_course(self, student_id: int, course_id: int) -> Certificate:
        """Requires 100% lesson completion and a passing final grade (if graded).
        Marks the enrollment completed and issues a certificate."""
        e = self.enrollments.find(student_id, course_id, ENROLLED)
        if not e:
            raise EnrollmentError("student is not actively enrolled in this course")
        if self.completion_percentage(student_id, course_id) < 100.0:
            raise ValidationError("all lessons must be completed first")
        if not self.grading.is_passing(student_id, course_id):
            raise ValidationError("final grade is below the passing grade")
        now = self.s.clock()
        grade = self.grading.final_grade(student_id, course_id)
        e.status, e.completed_at, e.final_grade = COMPLETED, now, grade
        cert = Certificate(uuid4().hex[:12].upper(), student_id, course_id, now,
                           grade if grade is not None else 100.0)
        self.s.certificates[(student_id, course_id)] = cert
        self.s.history.append(HistoryEvent(now, student_id, course_id, "course_completed",
                                           f"certificate {cert.code}"))
        return cert

    def certificate(self, student_id: int, course_id: int):
        return self.s.certificates.get((student_id, course_id))

    def learning_history(self, student_id: int) -> List[HistoryEvent]:
        if student_id not in self.s.students:
            raise NotFoundError(f"student {student_id} not found")
        return [h for h in self.s.history if h.student_id == student_id]
