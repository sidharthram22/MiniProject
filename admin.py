from django.contrib import admin
from .models import (
    Course, StudentProfile, Enrollment, Question, MockTest,
    TestAttempt, Bookmark, Leaderboard, WeeklyChallenge, ChallengeParticipation
)

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'category')
    search_fields = ('title', 'category')

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'email', 'role', 'total_score', 'accuracy', 'tests_taken', 'streak_days')
    search_fields = ('name', 'email')
    list_filter = ('role',)

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'course', 'enrolled_at')
    list_filter = ('course',)

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'course', 'question_text', 'correct_answer', 'difficulty')
    list_filter = ('course', 'difficulty')
    search_fields = ('question_text',)

@admin.register(MockTest)
class MockTestAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'user', 'course', 'difficulty', 'created_at')

@admin.register(TestAttempt)
class TestAttemptAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'course_name', 'score', 'total_questions', 'percentage', 'submitted_at')
    list_filter = ('course_name',)

@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'question', 'created_at')

@admin.register(Leaderboard)
class LeaderboardAdmin(admin.ModelAdmin):
    list_display = ('rank', 'student', 'total_score', 'updated_at')
    ordering = ('rank',)

@admin.register(WeeklyChallenge)
class WeeklyChallengeAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'course', 'week_start', 'week_end', 'active')
    list_filter = ('active', 'course')

@admin.register(ChallengeParticipation)
class ChallengeParticipationAdmin(admin.ModelAdmin):
    list_display = ('id', 'challenge', 'student', 'score', 'rank', 'completed_at')
