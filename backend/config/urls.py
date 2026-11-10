from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("core.urls")),
    path("api/auth/", include("accounts.urls")),
    path("api/candidates/", include("candidates.urls")),
    path("api/recruiters/", include("recruiters.urls")),
    path("api/resumes/", include("resumes.urls")),
    path("api/jobs/", include("jobs.urls")),
    path("api/matching/", include("matching.urls")),
    path("api/applications/", include("applications.urls")),
    path("api/skill-gap/", include("skillgap.urls"))
]