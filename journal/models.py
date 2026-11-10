from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Course(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='courses')
    title = models.CharField('Название курса или материала', max_length=180)
    platform = models.CharField('Платформа или автор', max_length=160)
    duration_hours = models.DecimalField(
        'Общая продолжительность в часах', max_digits=6, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-pk']
        verbose_name = 'Курс'
        verbose_name_plural = 'Курсы'
        constraints = [models.CheckConstraint(condition=models.Q(duration_hours__gt=0), name='course_duration_positive')]

    def __str__(self):
        return self.title


class LectureNote(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='notes')
    lesson_number = models.PositiveIntegerField('Номер урока', validators=[MinValueValidator(1)])
    topic = models.CharField('Тема урока', max_length=180)
    content = models.TextField('Краткое содержание и выводы')
    study_date = models.DateField('Дата изучения')

    class Meta:
        ordering = ['lesson_number', 'pk']
        verbose_name = 'Конспект'
        verbose_name_plural = 'Конспекты'
        constraints = [
            models.CheckConstraint(condition=models.Q(lesson_number__gt=0), name='lesson_number_positive'),
            models.UniqueConstraint(fields=['course', 'lesson_number'], name='unique_lesson_per_course'),
        ]

    def __str__(self):
        return f'{self.lesson_number}. {self.topic}'
