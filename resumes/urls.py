from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ResumeDocumentViewSet, ParseRunViewSet, ResumeUploadViewSet

router = DefaultRouter()
router.register(r"resume-documents", ResumeDocumentViewSet, basename="resume-document")
router.register(r"parse-runs", ParseRunViewSet, basename="parse-run")

upload_view = ResumeUploadViewSet.as_view({"post": "upload"})
bulk_upload_view = ResumeUploadViewSet.as_view({"post": "bulk_upload"})

urlpatterns = [
    path("", include(router.urls)),
    path("resumes/upload/", upload_view, name="resume-upload"),
    path("resumes/bulk-upload/", bulk_upload_view, name="resume-bulk-upload"),
]

