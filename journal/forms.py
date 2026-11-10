from django import forms
from django.utils import timezone

from .models import Course, LectureNote


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['title', 'platform', 'duration_hours']
        widgets = {'duration_hours': forms.NumberInput(attrs={'min': '0.01', 'step': '0.01'})}
        help_texts = {'duration_hours': 'Укажи полную длительность материала, например 12,5 часа.'}


class LectureNoteForm(forms.ModelForm):
    def __init__(self, *args, course, **kwargs):
        super().__init__(*args, **kwargs)
        # Course comes from an owner-filtered view, never from submitted fields.
        self.instance.course = course
        if not self.is_bound and not self.instance.pk:
            self.initial['study_date'] = timezone.localdate()

    class Meta:
        model = LectureNote
        fields = ['lesson_number', 'topic', 'content', 'study_date']
        widgets = {
            'lesson_number': forms.NumberInput(attrs={'min': 1}),
            'content': forms.Textarea(attrs={'rows': 7, 'placeholder': 'Что ты узнал? Какие идеи хочешь запомнить?'}),
            'study_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
        }

    def clean_lesson_number(self):
        number = self.cleaned_data['lesson_number']
        duplicates = LectureNote.objects.filter(course=self.instance.course, lesson_number=number)
        if self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise forms.ValidationError('Конспект с этим номером уже есть в курсе. Выбери другой номер.')
        return number

    def clean_study_date(self):
        value = self.cleaned_data['study_date']
        if value > timezone.localdate():
            raise forms.ValidationError('Дата изучения не может быть в будущем.')
        return value
