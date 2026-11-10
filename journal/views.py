from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Max, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .models import Course, LectureNote
from .forms import CourseForm, LectureNoteForm


def home(request):
    return render(request, 'journal/home.html')


@require_http_methods(['GET', 'POST'])
def signup(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = UserCreationForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, 'Аккаунт создан. Добавь первый курс!')
        return redirect('dashboard')
    return render(request, 'registration/signup.html', {'form': form})


@login_required
def dashboard(request):
    owned = Course.objects.filter(user=request.user)
    courses = owned.annotate(note_count=Count('notes'), last_studied=Max('notes__study_date'))
    stats = {
        'course_count': owned.count(),
        'note_count': LectureNote.objects.filter(course__user=request.user).count(),
        'hours': owned.aggregate(value=Sum('duration_hours'))['value'] or 0,
    }
    return render(request, 'journal/dashboard.html', {'courses': courses, 'stats': stats})


@login_required
def course_detail(request, pk):
    course = get_object_or_404(Course, pk=pk, user=request.user)
    notes = course.notes.all()
    return render(request, 'journal/course_detail.html', {'course': course, 'notes': notes, 'note_count': notes.count()})


@login_required
@require_http_methods(['GET', 'POST'])
def course_form(request, pk=None):
    course = get_object_or_404(Course, pk=pk, user=request.user) if pk is not None else Course(user=request.user)
    form = CourseForm(request.POST if request.method == 'POST' else None, instance=course)
    if request.method == 'POST' and form.is_valid():
        saved = form.save()
        messages.success(request, 'Курс сохранён.')
        return redirect('course_detail', pk=saved.pk)
    return render(request, 'journal/form.html', {
        'form': form, 'heading': 'Редактировать курс' if course.pk else 'Добавить курс',
        'intro': 'Сохрани материал, который изучаешь: курс, вебинар или книгу.',
        'course': course if course.pk else None,
    })


@login_required
@require_http_methods(['GET', 'POST'])
def note_form(request, course_pk=None, pk=None):
    if pk is not None:
        note = get_object_or_404(LectureNote.objects.select_related('course'), pk=pk, course__user=request.user)
        course = note.course
    else:
        course = get_object_or_404(Course, pk=course_pk, user=request.user)
        note = LectureNote(course=course)
    form = LectureNoteForm(request.POST if request.method == 'POST' else None, instance=note, course=course)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Конспект сохранён. Ещё одно открытие в дневнике!')
        return redirect('course_detail', pk=course.pk)
    return render(request, 'journal/form.html', {
        'form': form, 'heading': 'Редактировать конспект' if note.pk else 'Новый конспект',
        'intro': f'Курс: {course.title}', 'course': course,
    })


@login_required
@require_http_methods(['GET', 'POST'])
def course_delete(request, pk):
    course = get_object_or_404(Course, pk=pk, user=request.user)
    if request.method == 'POST':
        course.delete()
        messages.success(request, 'Курс и его конспекты удалены.')
        return redirect('dashboard')
    return render(request, 'journal/confirm_delete.html', {
        'heading': 'Удалить курс?', 'object_label': course.title, 'course': course,
        'warning': 'Все конспекты этого курса тоже будут удалены. Восстановить их будет нельзя.',
    })


@login_required
@require_http_methods(['GET', 'POST'])
def note_delete(request, pk):
    note = get_object_or_404(LectureNote.objects.select_related('course'), pk=pk, course__user=request.user)
    course = note.course
    if request.method == 'POST':
        note.delete()
        messages.success(request, 'Конспект удалён.')
        return redirect('course_detail', pk=course.pk)
    return render(request, 'journal/confirm_delete.html', {
        'heading': 'Удалить конспект?', 'object_label': str(note), 'course': course,
        'warning': 'Конспект будет удалён без возможности восстановления. Сам курс останется.',
    })
