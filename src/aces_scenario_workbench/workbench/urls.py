from __future__ import annotations

from django.urls import path

from . import api, collab, views

_REV = "scenarios/<slug:scenario_slug>/revisions/<int:revision_pk>/"
_OBJ = _REV + "objects/<str:object_type>/<str:object_stable_id>/"

urlpatterns = [
    path("", views.landing, name="landing"),
    path("healthz", views.healthz, name="healthz"),
    path("privacy/", views.privacy, name="privacy"),
    path("app/", views.spa_app, name="spa-app"),
    path("app/<path:path>", views.spa_app, name="spa-app-deep"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("scenarios/<slug:slug>/", views.scenario_detail, name="scenario-detail"),
    path("scenarios/<slug:slug>/activity/", views.scenario_activity, name="scenario-activity"),
    path(_REV, views.revision_overview, name="revision-overview"),
    path(_REV + "techniques/<str:technique_id>/", views.technique_detail, name="technique-detail"),
    path(_REV + "tactics/<str:tactic_id>/", views.tactic_detail, name="tactic-detail"),
    path(_REV + "modules/<str:path_step>/", views.step_detail, name="step-detail"),
    path(_REV + "evidence/<str:evidence_id>/", views.evidence_detail, name="evidence-detail"),
    path(_OBJ + "comment", collab.post_comment, name="object-comment"),
    path(_OBJ + "review-state", collab.set_review_state, name="object-review-state"),
    path(_OBJ + "decision", collab.record_decision, name="object-decision"),
    path("api/app/me", api.current_user, name="api-current-user"),
    path("api/app/scenarios", api.scenario_list, name="api-scenarios"),
    path("api/app/scenarios/<slug:slug>", api.scenario_detail, name="api-scenario-detail"),
    path(
        "api/app/revisions/<int:revision_pk>",
        api.revision_workspace,
        name="api-revision-workspace",
    ),
    path(
        "api/app/revisions/<int:revision_pk>/objects/<str:object_type>/<str:object_stable_id>/comments",
        api.post_object_comment,
        name="api-object-comment",
    ),
    path(
        "api/app/revisions/<int:revision_pk>/objects/<str:object_type>/<str:object_stable_id>/decisions",
        api.post_object_decision,
        name="api-object-decision",
    ),
    path(
        "api/scenarios/<slug:slug>/revisions",
        api.upload_revision,
        name="api-upload-revision",
    ),
]
