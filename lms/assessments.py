from __future__ import annotations

from typing import Dict, List, Optional

from .courses import CourseService
from .errors import AttemptLimitError, EnrollmentError, NotFoundError, ValidationError
from .models import (ASSIGNMENT, ENROLLED, QUIZ, SCORING_RULES, Assessment,
                     Attempt, HistoryEvent, Question)
from .store import Store


class AssessmentService:
    def __init__(self, store: Store, courses: CourseService):
        self.s = store
        self.courses = courses

    def create(self, course_id: int, title: str, kind: str, weight: float = 1.0,
               max_attempts: int = 1, scoring_rule: str = "best",
               max_points: float = 100.0) -> Assessment:
        self.courses.get(course_id)
        if kind not in (QUIZ, ASSIGNMENT):
            raise ValidationError(f"kind must be '{QUIZ}' or '{ASSIGNMENT}'")
        if not (title or "").strip():
            raise ValidationError("title is required")
        if weight <= 0:
            raise ValidationError("weight must be > 0")
        if max_attempts < 1:
            raise ValidationError("max_attempts must be >= 1")
        if scoring_rule not in SCORING_RULES:
            raise ValidationError(f"scoring_rule must be one of {SCORING_RULES}")
        if max_points <= 0:
            raise ValidationError("max_points must be > 0")
        a = Assessment(self.s.next_id(), course_id, title.strip(), kind, float(weight),
                       max_attempts, scoring_rule, float(max_points))
        self.s.assessments[a.id] = a
        return a

    def get(self, assessment_id: int) -> Assessment:
        try:
            return self.s.assessments[assessment_id]
        except KeyError:
            raise NotFoundError(f"assessment {assessment_id} not found")

    def add_question(self, assessment_id: int, text: str, choices: List[str],
                     correct_index: int, points: float = 1.0) -> Question:
        a = self.get(assessment_id)
        if a.kind != QUIZ:
            raise ValidationError("questions can only be added to quizzes")
        if len(choices) < 2:
            raise ValidationError("a question needs at least two choices")
        if not 0 <= correct_index < len(choices):
            raise ValidationError("correct_index out of range")
        if points <= 0:
            raise ValidationError("points must be > 0")
        q = Question(self.s.next_id(), text, list(choices), correct_index, float(points))
        a.questions.append(q)
        return q

    def attempts(self, assessment_id: int, student_id: int) -> List[Attempt]:
        return sorted((t for t in self.s.attempts.values()
                       if t.assessment_id == assessment_id and t.student_id == student_id),
                      key=lambda t: t.number)

    def attempts_remaining(self, assessment_id: int, student_id: int) -> int:
        a = self.get(assessment_id)
        return max(0, a.max_attempts - len(self.attempts(assessment_id, student_id)))

    def _begin(self, a: Assessment, student_id: int) -> int:
        if student_id not in self.s.students:
            raise NotFoundError(f"student {student_id} not found")
        enrolled = any(e.student_id == student_id and e.course_id == a.course_id and e.status == ENROLLED
                       for e in self.s.enrollments.values())
        if not enrolled:
            raise EnrollmentError("student must be actively enrolled to attempt assessments")
        used = len(self.attempts(a.id, student_id))
        if used >= a.max_attempts:
            raise AttemptLimitError(f"attempt limit of {a.max_attempts} reached")
        return used + 1

    def submit_quiz(self, assessment_id: int, student_id: int, answers: Dict[int, int]) -> Attempt:
        """answers maps question id -> chosen choice index. Auto-scored."""
        a = self.get(assessment_id)
        if a.kind != QUIZ:
            raise ValidationError("not a quiz")
        if not a.questions:
            raise ValidationError("quiz has no questions")
        valid = {q.id for q in a.questions}
        if set(answers) - valid:
            raise ValidationError("answers reference unknown questions")
        number = self._begin(a, student_id)
        score = sum(q.points for q in a.questions if answers.get(q.id) == q.correct_index)
        t = Attempt(self.s.next_id(), a.id, student_id, number, self.s.clock(),
                    score, a.total_points(), dict(answers))
        self.s.attempts[t.id] = t
        self.s.history.append(HistoryEvent(t.submitted_at, student_id, a.course_id, "quiz_submitted",
                                           f"{a.title}: {score}/{t.max_score}"))
        return t

    def submit_assignment(self, assessment_id: int, student_id: int) -> Attempt:
        """Records a submission; score stays None until an instructor grades it."""
        a = self.get(assessment_id)
        if a.kind != ASSIGNMENT:
            raise ValidationError("not an assignment")
        number = self._begin(a, student_id)
        t = Attempt(self.s.next_id(), a.id, student_id, number, self.s.clock(), None, a.max_points)
        self.s.attempts[t.id] = t
        self.s.history.append(HistoryEvent(t.submitted_at, student_id, a.course_id,
                                           "assignment_submitted", a.title))
        return t

    def grade_assignment(self, attempt_id: int, score: float, feedback: str = "") -> Attempt:
        try:
            t = self.s.attempts[attempt_id]
        except KeyError:
            raise NotFoundError(f"attempt {attempt_id} not found")
        a = self.get(t.assessment_id)
        if a.kind != ASSIGNMENT:
            raise ValidationError("only assignments are graded manually")
        if not 0 <= score <= a.max_points:
            raise ValidationError(f"score must be within 0..{a.max_points}")
        t.score, t.feedback = float(score), feedback
        self.s.history.append(HistoryEvent(self.s.clock(), t.student_id, a.course_id,
                                           "assignment_graded", f"{a.title}: {score}/{a.max_points}"))
        return t

    def effective_percent(self, assessment_id: int, student_id: int) -> Optional[float]:
        """Percent score after applying the assessment's scoring rule; None if nothing graded."""
        a = self.get(assessment_id)
        graded = [t for t in self.attempts(assessment_id, student_id) if t.percent is not None]
        if not graded:
            return None
        pcts = [t.percent for t in graded]
        if a.scoring_rule == "best":
            return max(pcts)
        if a.scoring_rule == "latest":
            return pcts[-1]
        return sum(pcts) / len(pcts)
