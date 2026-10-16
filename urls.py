from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='landing'),
    path('dashboard/', views.home, name='home'),
    path('admin-dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    # API endpoints for interactive AJAX test taking, PDF upload & administration
    path('api/start-test/', views.start_mock_test_api, name='start_test_api'),
    path('api/generate-from-pdf/', views.generate_pdf_mock_test_api, name='generate_pdf_mock_test_api'),
    path('api/submit-test/', views.submit_test_api, name='submit_test_api'),
    path('api/attempt-detail/<int:attempt_id>/', views.get_attempt_detail_api, name='get_attempt_detail_api'),
    path('api/toggle-bookmark/', views.toggle_bookmark_api, name='toggle_bookmark_api'),
    
    # Admin Management APIs
    path('api/admin/courses/', views.admin_get_courses_api, name='admin_get_courses_api'),
    path('api/admin/add-course/', views.admin_add_course_api, name='admin_add_course_api'),
    path('api/admin/edit-course/', views.admin_edit_course_api, name='admin_edit_course_api'),
    path('api/admin/delete-course/', views.admin_delete_course_api, name='admin_delete_course_api'),
    path('api/admin/course/<int:course_id>/questions/', views.admin_get_course_questions_api, name='admin_get_course_questions_api'),
    path('api/admin/add-question/', views.admin_add_question_api, name='admin_add_question_api'),
    path('api/admin/delete-question/', views.admin_delete_question_api, name='admin_delete_question_api'),
    path('api/admin/generate-questions/', views.admin_generate_questions_api, name='admin_generate_questions_api'),
]
