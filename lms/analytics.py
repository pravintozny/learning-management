from __future__ import annotations

from typing import Dict, List, Optional

from .courses import CourseService
from .enrollments import EnrollmentService
from .grading import GradingService
from .models import COMPLETED, DROPPED, ENROLLED
from .progress import ProgressService
from .store import Store


def _avg(xs: List[float]) -> Optional[float]:
    return round(sum(xs) / len(xs), 2) if xs else None


class AnalyticsService:
    def __init__(self, store: Store, courses: CourseService, enrollments: EnrollmentService,
                 grading: GradingService, progress: ProgressService):
        self.s, self.courses, self.enrollments = store, courses, enrollments
        self.grading, self.progress = grading, progress

    def student_performance(self, student_id: int) -> dict:
        es = [e for e in self.s.enrollments.values() if e.student_id == student_id]
        grades, per_course = [], []
        for e in es:
            if e.status == DROPPED:
                continue
            g = e.final_grade if e.status == COMPLETED else self.grading.final_grade(student_id, e.course_id)
            if g is not None:
                grades.append(g)
            per_course.append({"course_id": e.course_id, "status": e.status, "grade": g,
                               "progress": self.progress.completion_percentage(student_id, e.course_id)})
        return {"student_id": student_id,
                "courses_enrolled": len(es),
                "courses_completed": sum(1 for e in es if e.status == COMPLETED),
                "average_grade": _avg(grades),
                "courses": per_course}

    def course_completion_rate(self, course_id: int) -> Optional[float]:
        """Completed / (all non-dropped enrollments), as a percentage."""
        es = [e for e in self.enrollments.for_course(course_id) if e.status != DROPPED]
        if not es:
            return None
        return round(100.0 * sum(1 for e in es if e.status == COMPLETED) / len(es), 2)

    def enrollment_statistics(self, course_id: int) -> dict:
        c = self.courses.get(course_id)
        counts = {s: 0 for s in (ENROLLED, COMPLETED, DROPPED)}
        for e in self.enrollments.for_course(course_id):
            counts[e.status] += 1
        fill = None if c.capacity is None else round(100.0 * counts[ENROLLED] / c.capacity, 2)
        return {"course_id": course_id, "total": sum(counts.values()), **counts,
                "capacity": c.capacity, "fill_rate": fill,
                "revenue": round(c.price * (counts[ENROLLED] + counts[COMPLETED]), 2)}

    def instructor_performance(self, instructor_id: int) -> dict:
        cs = [c for c in self.s.courses.values() if c.instructor_id == instructor_id]
        students, grades, rates = set(), [], []
        for c in cs:
            for e in self.enrollments.for_course(c.id):
                if e.status == DROPPED:
                    continue
                students.add(e.student_id)
                g = e.final_grade if e.status == COMPLETED else None
                if g is not None:
                    grades.append(g)
            r = self.course_completion_rate(c.id)
            if r is not None:
                rates.append(r)
        return {"instructor_id": instructor_id, "courses": len(cs),
                "unique_students": len(students),
                "average_student_grade": _avg(grades),
                "average_completion_rate": _avg(rates)}

    def overview(self) -> Dict[int, dict]:
        return {c.id: {**self.enrollment_statistics(c.id),
                       "completion_rate": self.course_completion_rate(c.id)}
                for c in self.s.courses.values()}
