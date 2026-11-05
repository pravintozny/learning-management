from __future__ import annotations

from typing import List, Optional

from .errors import NotFoundError, PrerequisiteError, ValidationError
from .models import Category, Course, Lesson, Module
from .store import Store


class CourseService:
    def __init__(self, store: Store):
        self.s = store

    # categories
    def create_category(self, name: str) -> Category:
        name = (name or "").strip()
        if not name:
            raise ValidationError("category name is required")
        for c in self.s.categories.values():
            if c.name.lower() == name.lower():
                return c
        cat = Category(self.s.next_id(), name)
        self.s.categories[cat.id] = cat
        return cat

    # courses
    def create(self, title: str, price: float = 0.0, capacity: Optional[int] = None,
               category_id: Optional[int] = None, description: str = "",
               instructor_id: Optional[int] = None, passing_grade: float = 60.0) -> Course:
        if not (title or "").strip():
            raise ValidationError("title is required")
        if price < 0:
            raise ValidationError("price must be >= 0")
        if capacity is not None and capacity < 1:
            raise ValidationError("capacity must be >= 1 or None")
        if not 0 <= passing_grade <= 100:
            raise ValidationError("passing_grade must be within 0..100")
        if category_id is not None and category_id not in self.s.categories:
            raise NotFoundError(f"category {category_id} not found")
        if instructor_id is not None and instructor_id not in self.s.instructors:
            raise NotFoundError(f"instructor {instructor_id} not found")
        c = Course(self.s.next_id(), title.strip(), category_id, float(price), capacity,
                   description, instructor_id, [], [], float(passing_grade))
        self.s.courses[c.id] = c
        return c

    def get(self, course_id: int) -> Course:
        try:
            return self.s.courses[course_id]
        except KeyError:
            raise NotFoundError(f"course {course_id} not found")

    def set_price(self, course_id: int, price: float) -> Course:
        if price < 0:
            raise ValidationError("price must be >= 0")
        c = self.get(course_id)
        c.price = float(price)
        return c

    def set_capacity(self, course_id: int, capacity: Optional[int]) -> Course:
        c = self.get(course_id)
        if capacity is not None:
            if capacity < 1:
                raise ValidationError("capacity must be >= 1 or None")
            active = sum(1 for e in self.s.enrollments.values()
                         if e.course_id == course_id and e.status == "enrolled")
            if capacity < active:
                raise ValidationError(f"capacity {capacity} below current enrolled count {active}")
        c.capacity = capacity
        return c

    def catalog(self, category_id: Optional[int] = None, max_price: Optional[float] = None,
                search: str = "") -> List[Course]:
        out = []
        for c in self.s.courses.values():
            if category_id is not None and c.category_id != category_id:
                continue
            if max_price is not None and c.price > max_price:
                continue
            if search and search.lower() not in c.title.lower():
                continue
            out.append(c)
        return sorted(out, key=lambda c: c.id)

    # content
    def add_module(self, course_id: int, title: str) -> Module:
        if not (title or "").strip():
            raise ValidationError("module title is required")
        m = Module(self.s.next_id(), title.strip())
        self.get(course_id).modules.append(m)
        return m

    def add_lesson(self, course_id: int, module_id: int, title: str, duration_minutes: int = 0) -> Lesson:
        if not (title or "").strip():
            raise ValidationError("lesson title is required")
        if duration_minutes < 0:
            raise ValidationError("duration must be >= 0")
        for m in self.get(course_id).modules:
            if m.id == module_id:
                l = Lesson(self.s.next_id(), title.strip(), duration_minutes)
                m.lessons.append(l)
                return l
        raise NotFoundError(f"module {module_id} not found in course {course_id}")

    # prerequisites
    def add_prerequisite(self, course_id: int, prereq_id: int) -> Course:
        c = self.get(course_id)
        self.get(prereq_id)
        if course_id == prereq_id:
            raise PrerequisiteError("a course cannot be its own prerequisite")
        if prereq_id in c.prerequisites:
            return c
        if course_id in self.all_prerequisites(prereq_id):
            raise PrerequisiteError("prerequisite would create a cycle")
        c.prerequisites.append(prereq_id)
        return c

    def remove_prerequisite(self, course_id: int, prereq_id: int) -> Course:
        c = self.get(course_id)
        if prereq_id in c.prerequisites:
            c.prerequisites.remove(prereq_id)
        return c

    def all_prerequisites(self, course_id: int) -> set:
        """Transitive closure of prerequisites."""
        seen, stack = set(), list(self.get(course_id).prerequisites)
        while stack:
            p = stack.pop()
            if p not in seen:
                seen.add(p)
                stack.extend(self.get(p).prerequisites)
        return seen

    def missing_prerequisites(self, student_id: int, course_id: int) -> List[int]:
        """Direct prerequisites the student has not completed."""
        done = {e.course_id for e in self.s.enrollments.values()
                if e.student_id == student_id and e.status == "completed"}
        return [p for p in self.get(course_id).prerequisites if p not in done]
