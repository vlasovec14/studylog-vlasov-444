from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Max, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .models import Course, LectureNote


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
