"""In-memory data store shared by all services."""
from __future__ import annotations

import itertools
from datetime import datetime
from typing import Callable, Dict, List, Set, Tuple

from .models import (Assessment, Attempt, Category, Certificate, Course,
                     Enrollment, HistoryEvent, Instructor, Student)


class Store:
    def __init__(self, clock: Callable[[], datetime] = datetime.utcnow):
        self.clock = clock
        self._ids = itertools.count(1)
        self.students: Dict[int, Student] = {}
        self.instructors: Dict[int, Instructor] = {}
        self.categories: Dict[int, Category] = {}
        self.courses: Dict[int, Course] = {}
        self.enrollments: Dict[int, Enrollment] = {}
        self.assessments: Dict[int, Assessment] = {}
        self.attempts: Dict[int, Attempt] = {}
        self.history: List[HistoryEvent] = []
        self.certificates: Dict[Tuple[int, int], Certificate] = {}
        # (student_id, course_id) -> completed lesson ids
        self.completed_lessons: Dict[Tuple[int, int], Set[int]] = {}

    def next_id(self) -> int:
        return next(self._ids)
