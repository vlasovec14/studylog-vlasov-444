from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .forms import CourseForm, LectureNoteForm
from .models import Course, LectureNote


class StudyLogTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.owner = User.objects.create_user('nikita', password='StudyLog!444secure')
        cls.other = User.objects.create_user('other', password='Another!444secure')
        cls.course = Course.objects.create(user=cls.owner, title='Python для учебы', platform='Открытый курс', duration_hours=Decimal('12.50'))
        cls.foreign = Course.objects.create(user=cls.other, title='Чужой секретный курс', platform='Приватная платформа', duration_hours=10)
        cls.note = LectureNote.objects.create(course=cls.course, lesson_number=1, topic='Словари', content='Данные хранятся по ключам.', study_date=timezone.localdate())
        cls.foreign_note = LectureNote.objects.create(course=cls.foreign, lesson_number=1, topic='Чужая тема', content='Чужой конспект', study_date=timezone.localdate())

    def setUp(self):
        self.client.force_login(self.owner)

    def note_data(self, **extra):
        return {'lesson_number': 2, 'topic': 'Функции', 'content': 'Функция возвращает результат.', 'study_date': timezone.localdate().isoformat(), **extra}

    def course_data(self, **extra):
        return {'title': 'Django с нуля', 'platform': 'Вебинар', 'duration_hours': '5.50', **extra}

    def test_home_and_auth_pages_render(self):
        client = Client()
        for name in ['home', 'login', 'signup']:
            with self.subTest(name=name):
                self.assertEqual(client.get(reverse(name)).status_code, 200)

    def test_anonymous_access_requires_login(self):
        client = Client()
        targets = [('dashboard', []), ('course_add', []), ('course_detail', [self.course.pk]), ('course_edit', [self.course.pk]), ('course_delete', [self.course.pk]), ('note_add', [self.course.pk]), ('note_edit', [self.note.pk]), ('note_delete', [self.note.pk])]
        for name, args in targets:
            for method in ['get', 'post']:
                with self.subTest(name=name, method=method):
                    response = getattr(client, method)(reverse(name, args=args))
                    self.assertEqual(response.status_code, 302)
                    self.assertTrue(response.url.startswith(reverse('login')))

    def test_dashboard_shows_only_owned_courses_and_statistics(self):
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, self.course.title)
        self.assertNotContains(response, self.foreign.title)
        self.assertEqual(response.context['stats'], {'course_count': 1, 'note_count': 1, 'hours': Decimal('12.50')})

    def test_empty_dashboard(self):
        user = get_user_model().objects.create_user('new-user')
        self.client.force_login(user)
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, 'Начни с первого курса')
        self.assertEqual(response.context['stats']['hours'], 0)

    def test_owner_pages_render(self):
        targets = [('course_add', []), ('course_detail', [self.course.pk]), ('course_edit', [self.course.pk]), ('course_delete', [self.course.pk]), ('note_add', [self.course.pk]), ('note_edit', [self.note.pk]), ('note_delete', [self.note.pk])]
        for name, args in targets:
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name, args=args)).status_code, 200)

    def test_foreign_objects_cannot_be_read_modified_or_deleted(self):
        targets = [('course_detail', self.foreign.pk), ('course_edit', self.foreign.pk), ('course_delete', self.foreign.pk), ('note_add', self.foreign.pk), ('note_edit', self.foreign_note.pk), ('note_delete', self.foreign_note.pk)]
        for name, pk in targets:
            for method in ['get', 'post']:
                with self.subTest(name=name, method=method):
                    response = getattr(self.client, method)(reverse(name, args=[pk]), self.note_data())
                    self.assertEqual(response.status_code, 404)
        self.assertTrue(Course.objects.filter(pk=self.foreign.pk).exists())
        self.assertTrue(LectureNote.objects.filter(pk=self.foreign_note.pk).exists())

    def test_course_creation_ignores_submitted_owner(self):
        response = self.client.post(reverse('course_add'), self.course_data(user=self.other.pk))
        course = Course.objects.get(title='Django с нуля')
        self.assertEqual(course.user, self.owner)
        self.assertRedirects(response, reverse('course_detail', args=[course.pk]))

    def test_course_update_ignores_submitted_owner(self):
        self.client.post(reverse('course_edit', args=[self.course.pk]), self.course_data(user=self.other.pk))
        self.course.refresh_from_db()
        self.assertEqual(self.course.user, self.owner)
        self.assertEqual(self.course.title, 'Django с нуля')

    def test_invalid_course_data_stays_on_form(self):
        for duration in ['0', '-1', 'abc']:
            with self.subTest(duration=duration):
                response = self.client.post(reverse('course_add'), self.course_data(duration_hours=duration))
                self.assertEqual(response.status_code, 200)
                self.assertIn('duration_hours', response.context['form'].errors)
        self.assertEqual(Course.objects.filter(user=self.owner).count(), 1)

    def test_course_requires_nonblank_title_and_platform(self):
        form = CourseForm(data=self.course_data(title='   ', platform='   '))
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)
        self.assertIn('platform', form.errors)

    def test_note_creation_ignores_submitted_course(self):
        response = self.client.post(reverse('note_add', args=[self.course.pk]), self.note_data(course=self.foreign.pk))
        note = LectureNote.objects.get(course=self.course, lesson_number=2)
        self.assertEqual(note.course, self.course)
        self.assertRedirects(response, reverse('course_detail', args=[self.course.pk]))

    def test_note_edit_ignores_course_tampering(self):
        self.client.post(reverse('note_edit', args=[self.note.pk]), self.note_data(course=self.foreign.pk))
        self.note.refresh_from_db()
        self.assertEqual(self.note.course, self.course)
        self.assertEqual(self.note.topic, 'Функции')

    def test_nonpositive_and_fractional_lesson_numbers_rejected(self):
        for number in [0, -1, '1.5']:
            with self.subTest(number=number):
                form = LectureNoteForm(data=self.note_data(lesson_number=number), course=self.course)
                self.assertFalse(form.is_valid())
                self.assertIn('lesson_number', form.errors)

    def test_future_and_invalid_study_dates_rejected(self):
        for date in [(timezone.localdate() + timedelta(days=1)).isoformat(), '2026-02-30']:
            with self.subTest(date=date):
                form = LectureNoteForm(data=self.note_data(study_date=date), course=self.course)
                self.assertFalse(form.is_valid())
                self.assertIn('study_date', form.errors)

    def test_empty_note_content_rejected(self):
        form = LectureNoteForm(data=self.note_data(content='   '), course=self.course)
        self.assertFalse(form.is_valid())
        self.assertIn('content', form.errors)

    def test_duplicate_lesson_number_has_friendly_form_error(self):
        response = self.client.post(reverse('note_add', args=[self.course.pk]), self.note_data(lesson_number=1))
        self.assertEqual(response.status_code, 200)
        self.assertIn('lesson_number', response.context['form'].errors)

    def test_note_can_be_edited_with_unchanged_number(self):
        form = LectureNoteForm(data=self.note_data(lesson_number=1), instance=self.note, course=self.course)
        self.assertTrue(form.is_valid(), form.errors)

    def test_empty_post_is_bound_and_reports_errors(self):
        for name, args in [('course_add', []), ('note_add', [self.course.pk])]:
            response = self.client.post(reverse(name, args=args), {})
            self.assertTrue(response.context['form'].is_bound)
            self.assertTrue(response.context['form'].errors)

    def test_new_note_defaults_to_today_without_overwriting_existing_date(self):
        form = LectureNoteForm(course=self.course)
        self.assertEqual(form['study_date'].value(), timezone.localdate())
        self.note.study_date = timezone.localdate() - timedelta(days=3)
        self.note.save()
        edit_form = LectureNoteForm(instance=self.note, course=self.course)
        self.assertEqual(edit_form['study_date'].value(), self.note.study_date)

    def test_get_requests_do_not_delete_data(self):
        self.client.get(reverse('course_delete', args=[self.course.pk]))
        self.client.get(reverse('note_delete', args=[self.note.pk]))
        self.assertTrue(Course.objects.filter(pk=self.course.pk).exists())
        self.assertTrue(LectureNote.objects.filter(pk=self.note.pk).exists())

    def test_course_delete_cascades_only_its_notes(self):
        response = self.client.post(reverse('course_delete', args=[self.course.pk]))
        self.assertRedirects(response, reverse('dashboard'))
        self.assertFalse(LectureNote.objects.filter(pk=self.note.pk).exists())
        self.assertTrue(LectureNote.objects.filter(pk=self.foreign_note.pk).exists())

    def test_note_delete_preserves_course(self):
        self.client.post(reverse('note_delete', args=[self.note.pk]))
        self.assertFalse(LectureNote.objects.filter(pk=self.note.pk).exists())
        self.assertTrue(Course.objects.filter(pk=self.course.pk).exists())

    def test_csrf_enforced_on_mutations(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        targets = [('course_add', []), ('course_edit', [self.course.pk]), ('course_delete', [self.course.pk]), ('note_add', [self.course.pk]), ('note_edit', [self.note.pk]), ('note_delete', [self.note.pk]), ('logout', []), ('signup', [])]
        for name, args in targets:
            with self.subTest(name=name):
                self.assertEqual(client.post(reverse(name, args=args), self.note_data()).status_code, 403)
        client.get(reverse('course_add'))
        token = client.cookies['csrftoken'].value
        self.assertEqual(client.post(reverse('course_add'), self.course_data(), HTTP_X_CSRFTOKEN=token).status_code, 302)

    def test_signup_login_and_post_logout(self):
        client = Client()
        response = client.post(reverse('signup'), {'username': 'vlasov444', 'password1': 'Nikita!Study2026', 'password2': 'Nikita!Study2026'})
        self.assertRedirects(response, reverse('dashboard'))
        user = get_user_model().objects.get(username='vlasov444')
        self.assertTrue(user.check_password('Nikita!Study2026'))
        self.assertEqual(client.get(reverse('logout')).status_code, 405)
        self.assertRedirects(client.post(reverse('logout')), reverse('home'))
        response = client.post(reverse('login'), {'username': 'vlasov444', 'password': 'Nikita!Study2026'})
        self.assertRedirects(response, reverse('dashboard'))

    def test_invalid_registration_and_login(self):
        client = Client()
        response = client.post(reverse('signup'), {'username': 'nikita', 'password1': '123', 'password2': '123'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)
        response = client.post(reverse('login'), {'username': 'nikita', 'password': 'wrong'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)

    def test_login_rejects_external_redirect(self):
        client = Client()
        response = client.post(reverse('login'), {'username': 'nikita', 'password': 'StudyLog!444secure', 'next': 'https://example.org/steal'})
        self.assertRedirects(response, reverse('dashboard'))

    def test_note_html_is_escaped(self):
        self.note.content = '<script>alert(1)</script>'
        self.note.save()
        response = self.client.get(reverse('course_detail', args=[self.course.pk]))
        self.assertContains(response, '&lt;script&gt;')
        self.assertNotContains(response, '<script>alert(1)</script>')

    def test_database_rejects_zero_lesson_number(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            LectureNote.objects.create(course=self.course, lesson_number=0, topic='Zero', content='Test', study_date=timezone.localdate())

    def test_database_rejects_duplicate_lesson(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            LectureNote.objects.create(course=self.course, lesson_number=1, topic='Duplicate', content='Test', study_date=timezone.localdate())

    def test_database_rejects_zero_duration(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Course.objects.create(user=self.owner, title='Zero', platform='Test', duration_hours=0)

    def test_user_delete_cascades_courses_and_notes(self):
        self.owner.delete()
        self.assertFalse(Course.objects.filter(pk=self.course.pk).exists())
        self.assertFalse(LectureNote.objects.filter(pk=self.note.pk).exists())
        self.assertTrue(Course.objects.filter(pk=self.foreign.pk).exists())
