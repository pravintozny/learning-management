import unittest
from datetime import datetime, timedelta

from lms import LMS
from lms import errors as E
from lms.grading import letter_grade


def make_lms():
    t = [datetime(2026, 1, 1)]

    def clock():
        t[0] += timedelta(minutes=1)
        return t[0]
    return LMS(clock)


class Base(unittest.TestCase):
    def setUp(self):
        self.l = make_lms()
        self.alice = self.l.students.register("Alice", "alice@x.com")
        self.bob = self.l.students.register("Bob", "bob@x.com")
        self.ins = self.l.instructors.create("Ida", "ida@x.com", skills=["Python", " ML "])
        self.cat = self.l.courses.create_category("Programming")
        self.c1 = self.l.courses.create("Intro", 10, 1, self.cat.id, instructor_id=self.ins.id)
        m = self.l.courses.add_module(self.c1.id, "M1")
        self.les = [self.l.courses.add_lesson(self.c1.id, m.id, f"L{i}") for i in range(2)]
        self.c2 = self.l.courses.create("Advanced", 50, None, self.cat.id)
        self.l.courses.add_prerequisite(self.c2.id, self.c1.id)


class TestStudentsInstructors(Base):
    def test_register_validation_and_duplicates(self):
        with self.assertRaises(E.ValidationError):
            self.l.students.register("", "a@b.com")
        with self.assertRaises(E.ValidationError):
            self.l.students.register("X", "not-an-email")
        with self.assertRaises(E.DuplicateError):
            self.l.students.register("A2", "ALICE@x.com")

    def test_profile_update(self):
        self.l.students.update_profile(self.alice.id, name="Alice B", bio="hi")
        self.assertEqual(self.l.students.get(self.alice.id).name, "Alice B")
        with self.assertRaises(E.DuplicateError):
            self.l.students.update_profile(self.alice.id, email="bob@x.com")
        with self.assertRaises(E.NotFoundError):
            self.l.students.get(999)

    def test_instructor_skills_and_assignment(self):
        self.assertEqual(self.ins.skills, {"python", "ml"})
        self.l.instructors.add_skills(self.ins.id, ["SQL"])
        self.assertEqual(self.l.instructors.find_by_skill("sql"), [self.ins])
        self.l.instructors.remove_skill(self.ins.id, "ml")
        self.assertNotIn("ml", self.ins.skills)
        self.l.instructors.assign_course(self.ins.id, self.c2.id)
        self.assertEqual([c.id for c in self.l.instructors.courses_of(self.ins.id)], [self.c1.id, self.c2.id])
        self.l.instructors.unassign_course(self.c2.id)
        self.assertIsNone(self.c2.instructor_id)


class TestCourses(Base):
    def test_catalog_filters(self):
        self.assertEqual(len(self.l.courses.catalog(category_id=self.cat.id)), 2)
        self.assertEqual([c.id for c in self.l.courses.catalog(max_price=20)], [self.c1.id])
        self.assertEqual([c.id for c in self.l.courses.catalog(search="adv")], [self.c2.id])

    def test_validation(self):
        with self.assertRaises(E.ValidationError):
            self.l.courses.create("X", price=-1)
        with self.assertRaises(E.ValidationError):
            self.l.courses.create("X", capacity=0)
        with self.assertRaises(E.NotFoundError):
            self.l.courses.create("X", category_id=999)

    def test_prerequisite_cycles_rejected(self):
        with self.assertRaises(E.PrerequisiteError):
            self.l.courses.add_prerequisite(self.c1.id, self.c2.id)
        with self.assertRaises(E.PrerequisiteError):
            self.l.courses.add_prerequisite(self.c1.id, self.c1.id)
        c3 = self.l.courses.create("Expert")
        self.l.courses.add_prerequisite(c3.id, self.c2.id)
        self.assertEqual(self.l.courses.all_prerequisites(c3.id), {self.c1.id, self.c2.id})
        with self.assertRaises(E.PrerequisiteError):
            self.l.courses.add_prerequisite(self.c1.id, c3.id)

    def test_capacity_cannot_drop_below_enrolled(self):
        c = self.l.courses.create("Cap", capacity=3)
        for s in (self.alice, self.bob):
            self.l.enrollments.enroll(s.id, c.id)
        with self.assertRaises(E.ValidationError):
            self.l.courses.set_capacity(c.id, 1)
        self.l.courses.set_capacity(c.id, None)


class TestEnrollment(Base):
    def test_prerequisite_enforced(self):
        with self.assertRaises(E.PrerequisiteError):
            self.l.enrollments.enroll(self.alice.id, self.c2.id)
        self.finish(self.alice, self.c1)
        self.l.enrollments.enroll(self.alice.id, self.c2.id)

    def finish(self, student, course):
        self.l.enrollments.enroll(student.id, course.id)
        for les in course.lessons():
            self.l.progress.complete_lesson(student.id, course.id, les.id)
        return self.l.progress.complete_course(student.id, course.id)

    def test_capacity_and_reenroll_after_drop(self):
        self.l.enrollments.enroll(self.alice.id, self.c1.id)
        self.assertEqual(self.l.enrollments.seats_left(self.c1.id), 0)
        with self.assertRaises(E.EnrollmentError):
            self.l.enrollments.enroll(self.bob.id, self.c1.id)
        self.l.enrollments.drop(self.alice.id, self.c1.id)
        self.l.enrollments.enroll(self.bob.id, self.c1.id)
        self.assertEqual(self.l.enrollments.seats_left(self.c1.id), 0)

    def test_duplicate_and_completed(self):
        self.l.enrollments.enroll(self.alice.id, self.c1.id)
        with self.assertRaises(E.EnrollmentError):
            self.l.enrollments.enroll(self.alice.id, self.c1.id)
        for les in self.les:
            self.l.progress.complete_lesson(self.alice.id, self.c1.id, les.id)
        self.l.progress.complete_course(self.alice.id, self.c1.id)
        with self.assertRaises(E.EnrollmentError):
            self.l.enrollments.enroll(self.alice.id, self.c1.id)

    def test_drop_without_enrollment_and_history(self):
        with self.assertRaises(E.EnrollmentError):
            self.l.enrollments.drop(self.alice.id, self.c1.id)
        self.l.enrollments.enroll(self.alice.id, self.c1.id)
        self.l.enrollments.drop(self.alice.id, self.c1.id)
        h = self.l.students.enrollment_history(self.alice.id)
        self.assertEqual([e.status for e in h], ["dropped"])

    def test_unknown_student(self):
        with self.assertRaises(E.NotFoundError):
            self.l.enrollments.enroll(999, self.c1.id)


class TestAssessmentsAndGrading(Base):
    def setUp(self):
        super().setUp()
        self.l.courses.set_capacity(self.c1.id, 5)
        self.quiz = self.l.assessments.create(self.c1.id, "Quiz", "quiz", weight=1, max_attempts=2)
        self.q1 = self.l.assessments.add_question(self.quiz.id, "2+2", ["3", "4"], 1, 3)
        self.q2 = self.l.assessments.add_question(self.quiz.id, "1+1", ["2", "3"], 0, 1)
        self.asg = self.l.assessments.create(self.c1.id, "Essay", "assignment", weight=3, max_points=50)
        self.l.enrollments.enroll(self.alice.id, self.c1.id)

    def test_quiz_scoring_and_attempt_limit(self):
        t = self.l.assessments.submit_quiz(self.quiz.id, self.alice.id, {self.q1.id: 1, self.q2.id: 1})
        self.assertEqual((t.score, t.max_score, t.percent), (3, 4, 75.0))
        self.l.assessments.submit_quiz(self.quiz.id, self.alice.id, {self.q1.id: 1, self.q2.id: 0})
        with self.assertRaises(E.AttemptLimitError):
            self.l.assessments.submit_quiz(self.quiz.id, self.alice.id, {})
        self.assertEqual(self.l.assessments.effective_percent(self.quiz.id, self.alice.id), 100.0)

    def test_scoring_rules(self):
        a = self.l.assessments.create(self.c1.id, "r", "assignment", max_attempts=2, scoring_rule="average", max_points=10)
        t1 = self.l.assessments.submit_assignment(a.id, self.alice.id)
        t2 = self.l.assessments.submit_assignment(a.id, self.alice.id)
        self.l.assessments.grade_assignment(t1.id, 10)
        self.l.assessments.grade_assignment(t2.id, 5)
        self.assertEqual(self.l.assessments.effective_percent(a.id, self.alice.id), 75.0)
        a.scoring_rule = "latest"
        self.assertEqual(self.l.assessments.effective_percent(a.id, self.alice.id), 50.0)
        a.scoring_rule = "best"
        self.assertEqual(self.l.assessments.effective_percent(a.id, self.alice.id), 100.0)

    def test_must_be_enrolled(self):
        with self.assertRaises(E.EnrollmentError):
            self.l.assessments.submit_quiz(self.quiz.id, self.bob.id, {})

    def test_validation(self):
        with self.assertRaises(E.ValidationError):
            self.l.assessments.create(self.c1.id, "x", "exam")
        with self.assertRaises(E.ValidationError):
            self.l.assessments.add_question(self.asg.id, "q", ["a", "b"], 0)
        with self.assertRaises(E.ValidationError):
            self.l.assessments.add_question(self.quiz.id, "q", ["a", "b"], 5)
        with self.assertRaises(E.ValidationError):
            self.l.assessments.submit_quiz(self.quiz.id, self.alice.id, {12345: 0})
        t = self.l.assessments.submit_assignment(self.asg.id, self.alice.id)
        with self.assertRaises(E.ValidationError):
            self.l.assessments.grade_assignment(t.id, 51)

    def test_weighted_final_grade(self):
        self.l.assessments.submit_quiz(self.quiz.id, self.alice.id, {self.q1.id: 1, self.q2.id: 0})  # 100
        self.assertEqual(self.l.grading.final_grade(self.alice.id, self.c1.id), 25.0)  # asg ungraded = 0, 1/4 weight
        t = self.l.assessments.submit_assignment(self.asg.id, self.alice.id)
        self.l.assessments.grade_assignment(t.id, 40)  # 80%
        # (1*100 + 3*80)/4 = 85
        self.assertEqual(self.l.grading.final_grade(self.alice.id, self.c1.id), 85.0)
        self.assertEqual(self.l.grading.final_letter(self.alice.id, self.c1.id), "B")

    def test_letter_boundaries(self):
        self.assertEqual([letter_grade(x) for x in (95, 90, 89.99, 80, 70, 60, 59.9)],
                         ["A", "A", "B", "B", "C", "D", "F"])

    def test_no_assessments_final_grade_none(self):
        self.assertIsNone(self.l.grading.final_grade(self.alice.id, self.c2.id))


class TestProgress(Base):
    def setUp(self):
        super().setUp()
        self.l.enrollments.enroll(self.alice.id, self.c1.id)

    def test_percentage_and_idempotence(self):
        self.assertEqual(self.l.progress.complete_lesson(self.alice.id, self.c1.id, self.les[0].id), 50.0)
        self.assertEqual(self.l.progress.complete_lesson(self.alice.id, self.c1.id, self.les[0].id), 50.0)
        self.assertEqual(self.l.progress.completion_percentage(self.alice.id, self.c1.id), 50.0)

    def test_requires_enrollment_and_valid_lesson(self):
        with self.assertRaises(E.EnrollmentError):
            self.l.progress.complete_lesson(self.bob.id, self.c1.id, self.les[0].id)
        with self.assertRaises(E.NotFoundError):
            self.l.progress.complete_lesson(self.alice.id, self.c1.id, 9999)

    def test_cannot_complete_early_or_failing(self):
        with self.assertRaises(E.ValidationError):
            self.l.progress.complete_course(self.alice.id, self.c1.id)
        for les in self.les:
            self.l.progress.complete_lesson(self.alice.id, self.c1.id, les.id)
        a = self.l.assessments.create(self.c1.id, "Q", "assignment", max_points=10)
        with self.assertRaises(E.ValidationError):  # ungraded -> 0% < 60
            self.l.progress.complete_course(self.alice.id, self.c1.id)
        t = self.l.assessments.submit_assignment(a.id, self.alice.id)
        self.l.assessments.grade_assignment(t.id, 7)
        cert = self.l.progress.complete_course(self.alice.id, self.c1.id)
        self.assertEqual(cert.final_grade, 70.0)
        self.assertIs(self.l.progress.certificate(self.alice.id, self.c1.id), cert)
        self.assertEqual(len(cert.code), 12)

    def test_learning_history(self):
        self.l.progress.complete_lesson(self.alice.id, self.c1.id, self.les[0].id)
        kinds = [h.kind for h in self.l.progress.learning_history(self.alice.id)]
        self.assertEqual(kinds, ["registered", "enrolled", "lesson_completed"])


class TestAnalytics(Base):
    def test_stats(self):
        l = self.l
        l.courses.set_capacity(self.c1.id, 4)
        carol = l.students.register("Carol", "c@x.com")
        for s in (self.alice, self.bob, carol):
            l.enrollments.enroll(s.id, self.c1.id)
        a = l.assessments.create(self.c1.id, "A", "assignment", max_points=100)
        for les in self.les:
            l.progress.complete_lesson(self.alice.id, self.c1.id, les.id)
        t = l.assessments.submit_assignment(a.id, self.alice.id)
        l.assessments.grade_assignment(t.id, 90)
        l.progress.complete_course(self.alice.id, self.c1.id)
        l.enrollments.drop(carol.id, self.c1.id)

        st = l.analytics.enrollment_statistics(self.c1.id)
        self.assertEqual((st["total"], st["enrolled"], st["completed"], st["dropped"]), (3, 1, 1, 1))
        self.assertEqual(st["fill_rate"], 25.0)
        self.assertEqual(st["revenue"], 20.0)
        self.assertEqual(l.analytics.course_completion_rate(self.c1.id), 50.0)
        self.assertIsNone(l.analytics.course_completion_rate(self.c2.id))
        perf = l.analytics.student_performance(self.alice.id)
        self.assertEqual((perf["courses_completed"], perf["average_grade"]), (1, 90.0))
        ip = l.analytics.instructor_performance(self.ins.id)
        self.assertEqual((ip["courses"], ip["unique_students"], ip["average_student_grade"],
                          ip["average_completion_rate"]), (1, 2, 90.0, 50.0))
        self.assertIn(self.c1.id, l.analytics.overview())


if __name__ == "__main__":
    unittest.main()
