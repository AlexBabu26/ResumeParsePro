from django.urls import path
from .views import Page, LandingPageView

urlpatterns = [
    # Landing page (public, no auth required)
    path("", LandingPageView.as_view(), name="landing"),
    
    # Auth
    path("login/", Page.as_view(template_name="auth/login.html"), name="login"),
    path("register/", Page.as_view(template_name="auth/register.html"), name="register"),
    path("logout/", Page.as_view(template_name="auth/logout.html"), name="logout"),
    path("forgot-password/", Page.as_view(template_name="auth/forgot-password.html"), name="forgot-password"),
    path("reset-password/", Page.as_view(template_name="auth/reset-password.html"), name="reset-password"),

    # App pages (single template; page key controls content) - requires auth
    path("dashboard/", Page.as_view(template_name="page.html", extra_context={"page": "dashboard"}), name="dashboard"),

    path("resumes/upload/", Page.as_view(template_name="page.html", extra_context={"page": "upload"}), name="resume-upload"),
    path("resumes/documents/", Page.as_view(template_name="page.html", extra_context={"page": "documents"}), name="resume-documents"),

    path("resumes/parse-runs/", Page.as_view(template_name="page.html", extra_context={"page": "parse_runs"}), name="parse-runs"),
    path("resumes/parse-runs/<int:run_id>/", Page.as_view(template_name="page.html", extra_context={"page": "parse_run_detail"}), name="parse-run-detail"),

    path("candidates/", Page.as_view(template_name="page.html", extra_context={"page": "candidates_list"}), name="candidates-list"),
    path("candidates/<int:candidate_id>/", Page.as_view(template_name="page.html", extra_context={"page": "candidate_detail"}), name="candidate-detail"),
    path("candidates/<int:candidate_id>/edit-logs/", Page.as_view(template_name="page.html", extra_context={"page": "candidate_edit_logs"}), name="candidate-edit-logs"),

    path("profile/", Page.as_view(template_name="page.html", extra_context={"page": "profile"}), name="profile"),
    path("about/", Page.as_view(template_name="page.html", extra_context={"page": "about"}), name="about"),
]


