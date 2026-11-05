# learning-management

A dependency-free (Python 3.10+ standard library) in-memory Learning Management System.

```python
from lms import LMS
lms = LMS()
s = lms.students.register("Alice", "alice@example.com")
c = lms.courses.create("Intro", price=10, capacity=30)
lms.enrollments.enroll(s.id, c.id)
```

## Modules

| Area | Module | Service on `LMS` |
|---|---|---|
| Students (registration, profiles, enrollment history) | `lms/students.py` | `lms.students` |
| Instructors (profiles, skills, course assignment) | `lms/instructors.py` | `lms.instructors` |
| Courses (catalog, categories, modules/lessons, prerequisites, pricing) | `lms/courses.py` | `lms.courses` |
| Enrollment (status, dates, capacity) | `lms/enrollments.py` | `lms.enrollments` |
| Assessments (quizzes/assignments, scoring rules, attempt limits) | `lms/assessments.py` | `lms.assessments` |
| Grading (weighted grades, letters) | `lms/grading.py` | `lms.grading` |
| Progress (lessons, completion %, history, certificates) | `lms/progress.py` | `lms.progress` |
| Analytics | `lms/analytics.py` | `lms.analytics` |

See [docs/DESIGN.md](docs/DESIGN.md) for the business rules.

## Tests

```
python3 -m unittest discover -s tests -v
```
