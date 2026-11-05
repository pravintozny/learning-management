from __future__ import annotations

from typing import Dict, Optional

from .assessments import AssessmentService
from .courses import CourseService
from .store import Store

LETTER_SCALE = ((90, "A"), (80, "B"), (70, "C"), (60, "D"), (0, "F"))


def letter_grade(percent: float) -> str:
    for floor, letter in LETTER_SCALE:
        if percent >= floor:
            return letter
    return "F"


class GradingService:
    def __init__(self, store: Store, courses: CourseService, assessments: AssessmentService):
        self.s = store
        self.courses = courses
        self.assessments = assessments

    def course_assessments(self, course_id: int):
        return sorted((a for a in self.s.assessments.values() if a.course_id == course_id),
                      key=lambda a: a.id)

    def breakdown(self, student_id: int, course_id: int) -> Dict[int, Optional[float]]:
        """assessment id -> effective percent (None if not yet graded)."""
        return {a.id: self.assessments.effective_percent(a.id, student_id)
                for a in self.course_assessments(course_id)}

    def final_grade(self, student_id: int, course_id: int) -> Optional[float]:
        """Weighted average percent. Ungraded assessments count as 0.

        Returns None if the course has no assessments.
        """
        items = self.course_assessments(course_id)
        if not items:
            return None
        total_w = sum(a.weight for a in items)
        acc = 0.0
        for a in items:
            pct = self.assessments.effective_percent(a.id, student_id)
            acc += a.weight * (pct or 0.0)
        return round(acc / total_w, 2)

    def final_letter(self, student_id: int, course_id: int) -> Optional[str]:
        g = self.final_grade(student_id, course_id)
        return None if g is None else letter_grade(g)

    def is_passing(self, student_id: int, course_id: int) -> bool:
        g = self.final_grade(student_id, course_id)
        return True if g is None else g >= self.courses.get(course_id).passing_grade
