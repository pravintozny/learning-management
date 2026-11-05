"""Plain dataclasses describing the LMS domain."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set

# Enrollment statuses
ENROLLED = "enrolled"
COMPLETED = "completed"
DROPPED = "dropped"
ENROLLMENT_STATUSES = (ENROLLED, COMPLETED, DROPPED)

# Assessment kinds / scoring rules
QUIZ = "quiz"
ASSIGNMENT = "assignment"
SCORING_RULES = ("best", "latest", "average")


@dataclass
class Student:
    id: int
    name: str
    email: str
    registered_at: datetime
    bio: str = ""


@dataclass
class Instructor:
    id: int
    name: str
    email: str
    bio: str = ""
    skills: Set[str] = field(default_factory=set)


@dataclass
class Category:
    id: int
    name: str


@dataclass
class Lesson:
    id: int
    title: str
    duration_minutes: int = 0


@dataclass
class Module:
    id: int
    title: str
    lessons: List[Lesson] = field(default_factory=list)


@dataclass
class Course:
    id: int
    title: str
    category_id: Optional[int]
    price: float
    capacity: Optional[int]  # None == unlimited
    description: str = ""
    instructor_id: Optional[int] = None
    prerequisites: List[int] = field(default_factory=list)
    modules: List[Module] = field(default_factory=list)
    passing_grade: float = 60.0  # percent required for completion

    def lessons(self) -> List[Lesson]:
        return [l for m in self.modules for l in m.lessons]


@dataclass
class Enrollment:
    id: int
    student_id: int
    course_id: int
    status: str
    enrolled_at: datetime
    completed_at: Optional[datetime] = None
    dropped_at: Optional[datetime] = None
    final_grade: Optional[float] = None


@dataclass
class Question:
    id: int
    text: str
    choices: List[str]
    correct_index: int
    points: float = 1.0


@dataclass
class Assessment:
    id: int
    course_id: int
    title: str
    kind: str
    weight: float
    max_attempts: int = 1
    scoring_rule: str = "best"  # how multiple attempts combine
    max_points: float = 100.0  # used for assignments; quizzes derive from questions
    questions: List[Question] = field(default_factory=list)

    def total_points(self) -> float:
        if self.kind == QUIZ:
            return sum(q.points for q in self.questions)
        return self.max_points


@dataclass
class Attempt:
    id: int
    assessment_id: int
    student_id: int
    number: int
    submitted_at: datetime
    score: Optional[float]  # points; None until an assignment is graded
    max_score: float
    answers: Dict[int, int] = field(default_factory=dict)
    feedback: str = ""

    @property
    def percent(self) -> Optional[float]:
        if self.score is None or self.max_score <= 0:
            return None
        return 100.0 * self.score / self.max_score


@dataclass
class HistoryEvent:
    at: datetime
    student_id: int
    course_id: Optional[int]
    kind: str
    detail: str = ""


@dataclass
class Certificate:
    code: str
    student_id: int
    course_id: int
    issued_at: datetime
    final_grade: float
