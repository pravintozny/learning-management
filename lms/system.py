"""Facade wiring every service around one shared Store."""
from __future__ import annotations

from datetime import datetime
from typing import Callable

from .analytics import AnalyticsService
from .assessments import AssessmentService
from .courses import CourseService
from .enrollments import EnrollmentService
from .grading import GradingService
from .instructors import InstructorService
from .progress import ProgressService
from .store import Store
from .students import StudentService


class LMS:
    def __init__(self, clock: Callable[[], datetime] = datetime.utcnow):
        self.store = Store(clock)
        self.students = StudentService(self.store)
        self.instructors = InstructorService(self.store)
        self.courses = CourseService(self.store)
        self.enrollments = EnrollmentService(self.store, self.courses)
        self.assessments = AssessmentService(self.store, self.courses)
        self.grading = GradingService(self.store, self.courses, self.assessments)
        self.progress = ProgressService(self.store, self.courses, self.enrollments, self.grading)
        self.analytics = AnalyticsService(self.store, self.courses, self.enrollments,
                                          self.grading, self.progress)
