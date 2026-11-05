# Design & business rules

Storage is an in-memory `Store`; swap it for a persistence layer behind the services if needed.
All services raise subclasses of `lms.errors.LMSError`.

## Enrollment constraints
- Student and course must exist; no duplicate active enrollment; a completed course cannot be re-taken.
- All **direct prerequisites** must be *completed* by the student (`PrerequisiteError`).
- Prerequisite graphs must be acyclic (checked transitively when adding).
- Capacity counts `enrolled` students only; `None` = unlimited. Dropping frees a seat and a student may re-enroll after dropping. Capacity cannot be lowered below the current enrolled count.
- Statuses: `enrolled` -> `completed` | `dropped`.

## Assessments
- Kinds: `quiz` (auto-scored, points per question) and `assignment` (submitted, then graded manually 0..`max_points`).
- Only actively enrolled students may attempt; `max_attempts` is enforced (`AttemptLimitError`).
- `scoring_rule` combines graded attempts: `best`, `latest` or `average` (of percentages).

## Grading
- Final grade = `sum(weight_i * pct_i) / sum(weight_i)` over all assessments of the course; ungraded/unattempted count as 0%. Courses without assessments have no grade.
- Letters: A >= 90, B >= 80, C >= 70, D >= 60, else F.

## Progress & completion
- Completion % = completed lessons / total lessons (idempotent per lesson).
- `complete_course` requires 100% lessons and final grade >= course `passing_grade` (default 60); it marks the enrollment completed, stores the final grade and issues a certificate (random 12-char code).
- `learning_history` returns a chronological event log (registration, enrollment, lessons, submissions, grading, completion).

## Analytics
Student performance, per-course completion rate (completed / non-dropped), enrollment statistics (counts, fill rate, revenue), instructor performance (courses, unique students, average grade, average completion rate).
