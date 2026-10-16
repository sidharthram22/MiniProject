import os
import django
from datetime import date, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nptel_project.settings')
django.setup()

from core.models import (
    Course, StudentProfile, Enrollment, Question,
    Leaderboard, WeeklyChallenge
)
from core.ai_service import DEFAULT_QUESTION_BANK

def seed():
    print("Seeding NPTEL LITE Database...")
    
    # 1. Courses
    courses_data = [
        ("Data Structures", "Computer Science", "Fundamental data structures including stacks, queues, trees, and heaps."),
        ("DBMS", "Computer Science", "Relational algebra, SQL, normalization, and transaction management."),
        ("Computer Networks", "Computer Science", "OSI & TCP/IP layers, routing algorithms, ARP, IPv4/v6, and TCP/UDP."),
        ("Operating Systems", "Computer Science", "Process scheduling, deadlock handling, memory management, and concurrency."),
        ("Artificial Intelligence", "Computer Science", "Search algorithms, machine learning fundamentals, and neural networks.")
    ]

    course_objs = {}
    for title, cat, desc in courses_data:
        c, _ = Course.objects.get_or_create(title=title, defaults={'category': cat, 'description': desc})
        course_objs[title] = c

    # 2. Seed Default Questions
    for course_title, q_list in DEFAULT_QUESTION_BANK.items():
        if course_title in course_objs:
            c = course_objs[course_title]
            for q_data in q_list:
                Question.objects.get_or_create(
                    course=c,
                    question_text=q_data['question_text'],
                    defaults={
                        'option_a': q_data['option_a'],
                        'option_b': q_data['option_b'],
                        'option_c': q_data['option_c'],
                        'option_d': q_data['option_d'],
                        'correct_answer': q_data['correct_answer'],
                        'explanation': q_data['explanation'],
                        'difficulty': q_data['difficulty']
                    }
                )

    # 3. Seed Users (Students & Admin)
    users_data = [
        ("Aisha Sharma", "aisha@nptel.ac.in", "pass", "student", 980, "98.4%", 18, 5, "Data Structures • Moderate", ["Data Structures", "DBMS"]),
        ("Rohit Verma", "rohit@nptel.ac.in", "pass", "student", 950, "95.1%", 14, 4, "DBMS • Advanced", ["DBMS", "Operating Systems"]),
        ("Kavya Patel", "kavya@nptel.ac.in", "pass", "student", 890, "89.2%", 12, 3, "Computer Networks • Easy", ["Computer Networks", "Data Structures"]),
        ("Dev Kumar", "dev@nptel.ac.in", "pass", "student", 870, "87.0%", 10, 2, "Operating Systems • Medium", ["Operating Systems"]),
        ("Admin Portal", "admin@nptel.ac.in", "adminpass", "admin", 1200, "100%", 25, 10, "All Courses Administration", ["Data Structures", "DBMS", "Computer Networks", "Operating Systems", "Artificial Intelligence"])
    ]

    for name, email, pwd, role, total_score, acc, tests, streak, focus, enrolled in users_data:
        sp, created = StudentProfile.objects.get_or_create(
            email=email,
            defaults={
                'name': name,
                'password': pwd,
                'role': role,
                'total_score': total_score,
                'accuracy': acc,
                'tests_taken': tests,
                'streak_days': streak,
                'today_focus': focus
            }
        )
        if created or sp.total_score != total_score:
            sp.total_score = total_score
            sp.accuracy = acc
            sp.save()

        # Enrollments
        for c_title in enrolled:
            if c_title in course_objs:
                Enrollment.objects.get_or_create(student=sp, course=course_objs[c_title])

        # Leaderboard entry
        Leaderboard.objects.get_or_create(
            student=sp,
            defaults={'total_score': sp.total_score, 'rank': 1}
        )

    # Update Leaderboard ranks
    all_lbs = Leaderboard.objects.order_by('-total_score')
    for rank_idx, entry in enumerate(all_lbs, 1):
        entry.rank = rank_idx
        entry.save()

    # 4. Active Weekly Challenge
    ds_course = course_objs.get("Data Structures")
    if ds_course:
        today = date.today()
        WeeklyChallenge.objects.get_or_create(
            title="Weekly Sprint: Data Structures & Algorithms",
            course=ds_course,
            defaults={
                'description': "Complete 15 timed MCQs on Stacks, Queues, and BSTs to double your streak bonus points!",
                'week_start': today - timedelta(days=2),
                'week_end': today + timedelta(days=5),
                'active': True
            }
        )

    print("Seeding complete! Database ready for NPTEL LITE.")

if __name__ == '__main__':
    seed()
