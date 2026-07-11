from __future__ import annotations

from django.urls import path

from . import api, collab, views

_REV = "projects/<slug:project_slug>/scenarios/<slug:scenario_slug>/revisions/<int:revision_pk>/"
_OBJ = _REV + "objects/<str:object_type>/<str:object_stable_id>/"

urlpatterns = [
    path("", views.landing, name="landing"),
    path("healthz", views.healthz, name="healthz"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("projects/<slug:slug>/", views.project_detail, name="project-detail"),
    path("projects/<slug:slug>/activity/", views.project_activity, name="project-activity"),
    path(_REV, views.revision_overview, name="revision-overview"),
    path(_REV + "techniques/<str:technique_id>/", views.technique_detail, name="technique-detail"),
    path(_REV + "tactics/<str:tactic_id>/", views.tactic_detail, name="tactic-detail"),
    path(_REV + "modules/<str:path_step>/", views.step_detail, name="step-detail"),
    path(_REV + "evidence/<str:evidence_id>/", views.evidence_detail, name="evidence-detail"),
    path(_OBJ + "comment", collab.post_comment, name="object-comment"),
    path(_OBJ + "review-state", collab.set_review_state, name="object-review-state"),
    path(_OBJ + "decision", collab.record_decision, name="object-decision"),
    path(
        "api/projects/<slug:slug>/revisions",
        api.upload_revision,
        name="api-upload-revision",
    ),
]
