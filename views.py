import json
import random
from datetime import date, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseBadRequest
from django.db.models import Avg, Sum, Count
from django.views.decorators.csrf import csrf_exempt
from .models import (
    StudentProfile, Course, Enrollment, Question, MockTest,
    TestAttempt, Bookmark, Leaderboard, WeeklyChallenge, ChallengeParticipation
)
from .ai_service import (
    generate_mock_questions,
    extract_text_from_pdf_file,
    generate_questions_from_pdf_text
)

def get_current_user(request):
    user_email = request.session.get('user_email')
    if not user_email:
        return None
    try:
        return StudentProfile.objects.get(email=user_email)
    except StudentProfile.DoesNotExist:
        request.session.flush()
        return None

def index(request):
    # If already logged in, skip the landing page and go straight to dashboard
    user = get_current_user(request)
    if user:
        if user.is_admin():
            return redirect('admin_dashboard')
        return redirect('home')
    return render(request, 'home.html')

def login_view(request):
    user = get_current_user(request)
    if user:
        if user.is_admin():
            return redirect('admin_dashboard')
        return redirect('home')

    error = None
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')

        try:
            student = StudentProfile.objects.get(email=email, password=password)
            request.session['user_email'] = student.email
            if student.is_admin():
                return redirect('admin_dashboard')
            return redirect('home')
        except StudentProfile.DoesNotExist:
            error = "Invalid email or password. Please check your credentials or register."

    demo_students = StudentProfile.objects.all()[:5]
    return render(request, 'login.html', {'error': error, 'demo_students': demo_students})

def register_view(request):
    user = get_current_user(request)
    if user:
        if user.is_admin():
            return redirect('admin_dashboard')
        return redirect('home')

    error = None
    all_courses = Course.objects.all()

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        role = request.POST.get('role', 'student')
        selected_course_ids = request.POST.getlist('courses')

        if not name or not email or not password:
            error = "Please fill in all required fields."
        elif StudentProfile.objects.filter(email=email).exists():
            error = "An account with this email address already exists."
        else:
            first_course = Course.objects.filter(id__in=selected_course_ids).first()
            today_focus = f"{first_course.title if first_course else 'Data Structures'} • Easy"

            student = StudentProfile.objects.create(
                name=name,
                email=email,
                password=password,
                role=role,
                today_focus=today_focus
            )

            for course_id in selected_course_ids:
                try:
                    course = Course.objects.get(id=course_id)
                    Enrollment.objects.get_or_create(student=student, course=course)
                except Course.DoesNotExist:
                    pass

            Leaderboard.objects.get_or_create(student=student, total_score=0, rank=99)

            request.session['user_email'] = student.email
            if student.is_admin():
                return redirect('admin_dashboard')
            return redirect('home')

    return render(request, 'register.html', {'error': error, 'courses': all_courses})

def logout_view(request):
    request.session.flush()
    return redirect('login')

def admin_dashboard_view(request):
    user = get_current_user(request)
    if not user or not user.is_admin():
        return redirect('home')

    all_courses = Course.objects.all()
    all_students = StudentProfile.objects.all().order_by('-created_at')

    admin_metrics = {
        'total_students': StudentProfile.objects.filter(role='student').count(),
        'total_courses': Course.objects.count(),
        'total_questions': Question.objects.count(),
        'total_tests_taken': TestAttempt.objects.count(),
        'total_enrollments': Enrollment.objects.count(),
    }

    admin_courses = []
    for c in Course.objects.annotate(
        q_count=Count('questions', distinct=True),
        e_count=Count('student_enrollments', distinct=True)
    ).order_by('-id'):
        admin_courses.append({
            'id': c.id,
            'title': c.title,
            'category': c.category,
            'description': c.description or '',
            'question_count': c.q_count,
            'enrollment_count': c.e_count,
        })

    context = {
        'user': user,
        'all_courses': all_courses,
        'all_students': all_students,
        'admin_metrics': admin_metrics,
        'admin_courses': admin_courses,
    }
    return render(request, 'admin_dashboard.html', context)

def home(request):
    user = get_current_user(request)
    if not user:
        return redirect('login')

    all_courses = Course.objects.all()
    enrolled_courses = user.enrolled_courses_list()

    actual_attempts_count = TestAttempt.objects.filter(student=user).count()
    if user.tests_taken < actual_attempts_count:
        user.tests_taken = actual_attempts_count
        user.save()

    top_leaderboard = Leaderboard.objects.select_related('student').order_by('-total_score')[:5]
    leaderboard_data = []
    for idx, lb in enumerate(top_leaderboard, 1):
        leaderboard_data.append({
            'rank': idx,
            'name': lb.student.name,
            'score': lb.total_score,
            'is_current': lb.student.email == user.email
        })

    active_challenge = WeeklyChallenge.objects.filter(active=True).first()
    user_bookmarks = Bookmark.objects.filter(student=user).select_related('question', 'question__course')
    attempts = TestAttempt.objects.filter(student=user).order_by('-submitted_at')

    admin_metrics = {}
    admin_courses = []
    if user.is_admin():
        admin_metrics = {
            'total_students': StudentProfile.objects.filter(role='student').count(),
            'total_courses': Course.objects.count(),
            'total_questions': Question.objects.count(),
            'total_tests_taken': TestAttempt.objects.count(),
            'total_enrollments': Enrollment.objects.count(),
        }
        for c in Course.objects.annotate(
            q_count=Count('questions', distinct=True),
            e_count=Count('student_enrollments', distinct=True)
        ).order_by('-id'):
            admin_courses.append({
                'id': c.id,
                'title': c.title,
                'category': c.category,
                'description': c.description or '',
                'question_count': c.q_count,
                'enrollment_count': c.e_count,
            })

    context = {
        'user': user,
        'all_courses': all_courses,
        'enrolled_courses': enrolled_courses,
        'leaderboard': leaderboard_data,
        'active_challenge': active_challenge,
        'user_bookmarks': user_bookmarks,
        'attempts': attempts,
        'admin_metrics': admin_metrics,
        'admin_courses': admin_courses,
    }
    return render(request, 'index.html', context)

@csrf_exempt
def start_mock_test_api(request):
    user = get_current_user(request)
    if not user:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    course_id = request.GET.get('course_id')
    difficulty = request.GET.get('difficulty', 'Medium')
    count = int(request.GET.get('count', 5))

    if course_id:
        course = get_object_or_404(Course, id=course_id)
    else:
        course = Course.objects.first()
        if not course:
            course = Course.objects.create(title="Data Structures", category="Computer Science")

    ai_generated = generate_mock_questions(course.title, difficulty=difficulty, count=count)
    questions_list = []

    for q_data in ai_generated:
        q_obj, created = Question.objects.get_or_create(
            course=course,
            question_text=q_data['question_text'],
            defaults={
                'option_a': q_data['option_a'],
                'option_b': q_data['option_b'],
                'option_c': q_data['option_c'],
                'option_d': q_data['option_d'],
                'correct_answer': q_data['correct_answer'],
                'explanation': q_data['explanation'],
                'difficulty': difficulty
            }
        )
        is_bookmarked = Bookmark.objects.filter(student=user, question=q_obj).exists()
        questions_list.append({
            'id': q_obj.id,
            'question_text': q_obj.question_text,
            'option_a': q_obj.option_a,
            'option_b': q_obj.option_b,
            'option_c': q_obj.option_c,
            'option_d': q_obj.option_d,
            'correct_answer': q_obj.correct_answer,
            'explanation': q_obj.explanation,
            'is_bookmarked': is_bookmarked
        })

    mock_test = MockTest.objects.create(
        user=user,
        course=course,
        title=f"{course.title} • {difficulty} AI Mock Test",
        difficulty=difficulty,
        duration_minutes=max(5, count * 2)
    )

    return JsonResponse({
        'test_id': mock_test.id,
        'course_title': course.title,
        'difficulty': difficulty,
        'duration_minutes': mock_test.duration_minutes,
        'questions': questions_list
    })

@csrf_exempt
def generate_pdf_mock_test_api(request):
    """
    Receives an uploaded PDF file, extracts its content, analyzes it with Claude API,
    and returns a custom AI-generated mock test matching the requested question count.
    """
    user = get_current_user(request)
    if not user or request.method != 'POST':
        return JsonResponse({'error': 'Unauthorized or Invalid request'}, status=400)

    pdf_file = request.FILES.get('pdf_file')
    count = int(request.POST.get('count', 5))
    difficulty = request.POST.get('difficulty', 'Medium')
    course_id = request.POST.get('course_id')

    if not pdf_file:
        return JsonResponse({'error': 'Please select a PDF file to upload'}, status=400)

    pdf_text = extract_text_from_pdf_file(pdf_file)
    if not pdf_text:
        pdf_text = f"Study material document: {pdf_file.name}"

    if course_id:
        course = get_object_or_404(Course, id=course_id)
    else:
        course, _ = Course.objects.get_or_create(title="PDF Document Analysis", category="Custom Upload")

    ai_generated = generate_questions_from_pdf_text(pdf_text, count=count, difficulty=difficulty)

    questions_list = []
    for q_data in ai_generated:
        q_obj = Question.objects.create(
            course=course,
            question_text=q_data['question_text'],
            option_a=q_data['option_a'],
            option_b=q_data['option_b'],
            option_c=q_data['option_c'],
            option_d=q_data['option_d'],
            correct_answer=q_data['correct_answer'],
            explanation=q_data['explanation'],
            difficulty=difficulty
        )
        questions_list.append({
            'id': q_obj.id,
            'question_text': q_obj.question_text,
            'option_a': q_obj.option_a,
            'option_b': q_obj.option_b,
            'option_c': q_obj.option_c,
            'option_d': q_obj.option_d,
            'correct_answer': q_obj.correct_answer,
            'explanation': q_obj.explanation,
            'is_bookmarked': False
        })

    mock_test = MockTest.objects.create(
        user=user,
        course=course,
        title=f"PDF Test: {pdf_file.name[:25]} • {difficulty}",
        difficulty=difficulty,
        duration_minutes=max(5, count * 2)
    )

    return JsonResponse({
        'test_id': mock_test.id,
        'course_title': f"PDF: {pdf_file.name[:25]}",
        'difficulty': difficulty,
        'duration_minutes': mock_test.duration_minutes,
        'questions': questions_list
    })

@csrf_exempt
def submit_test_api(request):
    user = get_current_user(request)
    if not user or request.method != 'POST':
        return JsonResponse({'error': 'Unauthorized or Invalid method'}, status=400)

    try:
        data = json.loads(request.body)
        test_id = data.get('test_id')
        user_answers = data.get('answers', {})
        duration_taken = int(data.get('duration_taken_seconds', 120))

        mock_test = MockTest.objects.filter(id=test_id).first() if test_id else None
        course_name = mock_test.course.title if mock_test else "NPTEL Mock Test"

        correct_count = 0
        total_questions = len(user_answers)
        detailed_results = []

        for q_id_str, user_ans in user_answers.items():
            try:
                question = Question.objects.get(id=int(q_id_str))
                is_correct = (str(user_ans).upper() == str(question.correct_answer).upper())
                if is_correct:
                    correct_count += 1

                detailed_results.append({
                    'question_id': question.id,
                    'question_text': question.question_text,
                    'user_answer': user_ans,
                    'correct_answer': question.correct_answer,
                    'is_correct': is_correct,
                    'explanation': question.explanation,
                    'options': {
                        'A': question.option_a,
                        'B': question.option_b,
                        'C': question.option_c,
                        'D': question.option_d
                    }
                })
            except Question.DoesNotExist:
                pass

        percentage = round((correct_count / total_questions * 100), 1) if total_questions > 0 else 0.0
        earned_score = correct_count * 50

        attempt = TestAttempt.objects.create(
            test=mock_test,
            student=user,
            course_name=course_name,
            score=earned_score,
            total_questions=total_questions,
            percentage=percentage,
            duration_taken_seconds=duration_taken,
            answers_json=json.dumps(detailed_results)
        )

        user.tests_taken = TestAttempt.objects.filter(student=user).count()
        user.total_score += earned_score
        user.streak_days += 1

        all_attempts = TestAttempt.objects.filter(student=user)
        avg_acc = all_attempts.aggregate(Avg('percentage'))['percentage__avg'] or percentage
        user.accuracy = f"{round(avg_acc, 1)}%"
        user.save()

        lb_entry, created = Leaderboard.objects.get_or_create(student=user)
        lb_entry.total_score = user.total_score
        lb_entry.save()

        all_lbs = Leaderboard.objects.order_by('-total_score')
        for rank_idx, entry in enumerate(all_lbs, 1):
            if entry.rank != rank_idx:
                entry.rank = rank_idx
                entry.save()

        return JsonResponse({
            'success': True,
            'attempt_id': attempt.id,
            'score': earned_score,
            'correct_count': correct_count,
            'total_questions': total_questions,
            'percentage': percentage,
            'new_total_score': user.total_score,
            'new_accuracy': user.accuracy,
            'new_streak': user.streak_days,
            'new_tests_taken': user.tests_taken,
            'results': detailed_results
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def get_attempt_detail_api(request, attempt_id):
    user = get_current_user(request)
    if not user:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    attempt = get_object_or_404(TestAttempt, id=attempt_id, student=user)
    results = json.loads(attempt.answers_json) if attempt.answers_json else []

    return JsonResponse({
        'attempt_id': attempt.id,
        'course_name': attempt.course_name,
        'score': attempt.score,
        'total_questions': attempt.total_questions,
        'percentage': attempt.percentage,
        'duration_taken_seconds': attempt.duration_taken_seconds,
        'submitted_at': attempt.submitted_at.strftime('%b %d, %Y %H:%M'),
        'results': results
    })

@csrf_exempt
def toggle_bookmark_api(request):
    user = get_current_user(request)
    if not user or request.method != 'POST':
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    data = json.loads(request.body)
    question_id = data.get('question_id')
    question = get_object_or_404(Question, id=question_id)

    bookmark, created = Bookmark.objects.get_or_create(student=user, question=question)
    if not created:
        bookmark.delete()
        is_bookmarked = False
    else:
        is_bookmarked = True

    return JsonResponse({'success': True, 'is_bookmarked': is_bookmarked, 'question_id': question.id})

@csrf_exempt
def admin_get_courses_api(request):
    user = get_current_user(request)
    if not user or not user.is_admin():
        return JsonResponse({'error': 'Admin privileges required'}, status=403)

    courses = Course.objects.annotate(
        q_count=Count('questions', distinct=True),
        e_count=Count('student_enrollments', distinct=True)
    ).order_by('-id')

    course_list = []
    for c in courses:
        course_list.append({
            'id': c.id,
            'title': c.title,
            'category': c.category,
            'description': c.description or '',
            'question_count': c.q_count,
            'enrollment_count': c.e_count,
        })

    return JsonResponse({'success': True, 'courses': course_list})

@csrf_exempt
def admin_add_course_api(request):
    user = get_current_user(request)
    if not user or not user.is_admin() or request.method != 'POST':
        return JsonResponse({'error': 'Admin privileges required'}, status=403)

    try:
        data = json.loads(request.body)
        title = data.get('title', '').strip()
        category = data.get('category', 'Computer Science').strip()
        description = data.get('description', '').strip()
        auto_generate = data.get('auto_generate', True)

        if not title:
            return JsonResponse({'error': 'Course title is required'}, status=400)

        course, created = Course.objects.get_or_create(
            title=title,
            defaults={'category': category, 'description': description}
        )

        if not created:
            return JsonResponse({'error': f'Course "{title}" already exists in database.'}, status=400)

        if auto_generate:
            generate_mock_questions(course.title, difficulty="Medium", count=5)

        return JsonResponse({
            'success': True,
            'course': {
                'id': course.id,
                'title': course.title,
                'category': course.category,
                'description': course.description,
                'question_count': course.questions.count(),
                'enrollment_count': course.student_enrollments.count()
            }
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def admin_edit_course_api(request):
    user = get_current_user(request)
    if not user or not user.is_admin() or request.method != 'POST':
        return JsonResponse({'error': 'Admin privileges required'}, status=403)

    try:
        data = json.loads(request.body)
        course_id = data.get('course_id')
        title = data.get('title', '').strip()
        category = data.get('category', 'Computer Science').strip()
        description = data.get('description', '').strip()

        if not course_id or not title:
            return JsonResponse({'error': 'Course ID and Title are required'}, status=400)

        course = get_object_or_404(Course, id=course_id)
        if Course.objects.filter(title=title).exclude(id=course_id).exists():
            return JsonResponse({'error': f'Another course with title "{title}" already exists.'}, status=400)

        course.title = title
        course.category = category
        course.description = description
        course.save()

        return JsonResponse({
            'success': True,
            'course': {
                'id': course.id,
                'title': course.title,
                'category': course.category,
                'description': course.description,
                'question_count': course.questions.count(),
                'enrollment_count': course.student_enrollments.count()
            }
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def admin_delete_course_api(request):
    user = get_current_user(request)
    if not user or not user.is_admin() or request.method != 'POST':
        return JsonResponse({'error': 'Admin privileges required'}, status=403)

    try:
        data = json.loads(request.body)
        course_id = data.get('course_id')
        if not course_id:
            return JsonResponse({'error': 'Course ID is required'}, status=400)

        course = get_object_or_404(Course, id=course_id)
        course_title = course.title
        course.delete()

        return JsonResponse({'success': True, 'deleted_title': course_title, 'course_id': course_id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def admin_get_course_questions_api(request, course_id):
    user = get_current_user(request)
    if not user or not user.is_admin():
        return JsonResponse({'error': 'Admin privileges required'}, status=403)

    course = get_object_or_404(Course, id=course_id)
    questions = Question.objects.filter(course=course).order_by('-created_at')

    q_list = []
    for q in questions:
        q_list.append({
            'id': q.id,
            'question_text': q.question_text,
            'option_a': q.option_a,
            'option_b': q.option_b,
            'option_c': q.option_c,
            'option_d': q.option_d,
            'correct_answer': q.correct_answer,
            'explanation': q.explanation,
            'difficulty': q.difficulty
        })

    return JsonResponse({
        'success': True,
        'course_id': course.id,
        'course_title': course.title,
        'questions': q_list
    })

@csrf_exempt
def admin_add_question_api(request):
    user = get_current_user(request)
    if not user or not user.is_admin() or request.method != 'POST':
        return JsonResponse({'error': 'Admin privileges required'}, status=403)

    data = json.loads(request.body)
    course_id = data.get('course_id')
    question_text = data.get('question_text', '').strip()
    option_a = data.get('option_a', '').strip()
    option_b = data.get('option_b', '').strip()
    option_c = data.get('option_c', '').strip()
    option_d = data.get('option_d', '').strip()
    correct_answer = data.get('correct_answer', 'A').upper()
    explanation = data.get('explanation', '').strip()
    difficulty = data.get('difficulty', 'Medium')

    course = get_object_or_404(Course, id=course_id)

    q = Question.objects.create(
        course=course,
        question_text=question_text,
        option_a=option_a,
        option_b=option_b,
        option_c=option_c,
        option_d=option_d,
        correct_answer=correct_answer,
        explanation=explanation,
        difficulty=difficulty
    )

    return JsonResponse({
        'success': True,
        'question_id': q.id,
        'question': {
            'id': q.id,
            'question_text': q.question_text,
            'option_a': q.option_a,
            'option_b': q.option_b,
            'option_c': q.option_c,
            'option_d': q.option_d,
            'correct_answer': q.correct_answer,
            'explanation': q.explanation,
            'difficulty': q.difficulty
        }
    })

@csrf_exempt
def admin_delete_question_api(request):
    user = get_current_user(request)
    if not user or not user.is_admin() or request.method != 'POST':
        return JsonResponse({'error': 'Admin privileges required'}, status=403)

    try:
        data = json.loads(request.body)
        question_id = data.get('question_id')
        question = get_object_or_404(Question, id=question_id)
        course_id = question.course.id
        question.delete()
        return JsonResponse({'success': True, 'question_id': question_id, 'course_id': course_id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def admin_generate_questions_api(request):
    user = get_current_user(request)
    if not user or not user.is_admin() or request.method != 'POST':
        return JsonResponse({'error': 'Admin privileges required'}, status=403)

    try:
        data = json.loads(request.body)
        course_id = data.get('course_id')
        count = int(data.get('count', 5))
        difficulty = data.get('difficulty', 'Medium')

        course = get_object_or_404(Course, id=course_id)
        ai_generated = generate_mock_questions(course.title, difficulty=difficulty, count=count)

        created_count = 0
        for q_data in ai_generated:
            Question.objects.create(
                course=course,
                question_text=q_data['question_text'],
                option_a=q_data['option_a'],
                option_b=q_data['option_b'],
                option_c=q_data['option_c'],
                option_d=q_data['option_d'],
                correct_answer=q_data['correct_answer'],
                explanation=q_data['explanation'],
                difficulty=difficulty
            )
            created_count += 1

        return JsonResponse({
            'success': True,
            'course_id': course.id,
            'course_title': course.title,
            'created_count': created_count,
            'total_questions': course.questions.count()
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
