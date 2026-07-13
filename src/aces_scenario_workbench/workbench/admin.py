from __future__ import annotations

from django.contrib import admin

from .models import (
    ActivityEvent,
    Challenge,
    ChallengeEvidenceRequirement,
    Comment,
    Decision,
    Evidence,
    Membership,
    ReviewState,
    Revision,
    Scenario,
    Step,
    Tactic,
    Technique,
)


class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 0
    autocomplete_fields = ("user",)


@admin.register(Scenario)
class ScenarioAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "created_at")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    inlines = (MembershipInline,)


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("scenario", "user", "role")
    list_filter = ("role",)
    search_fields = ("scenario__name", "user__email")


@admin.register(Revision)
class RevisionAdmin(admin.ModelAdmin):
    list_display = ("label", "scenario", "mapping_id", "content_digest", "created_at")
    list_filter = ("scenario",)
    search_fields = ("label", "mapping_id", "content_digest")


@admin.register(Tactic)
class TacticAdmin(admin.ModelAdmin):
    list_display = ("tactic_id", "name", "revision")
    search_fields = ("tactic_id", "name")


@admin.register(Step)
class StepAdmin(admin.ModelAdmin):
    list_display = ("path_step", "surface", "tier", "revision")
    search_fields = ("path_step", "behavior_specification")


@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    list_display = ("evidence_id", "revision")
    search_fields = ("evidence_id",)


@admin.register(Technique)
class TechniqueAdmin(admin.ModelAdmin):
    list_display = ("technique_id", "name", "surface", "coverage_status", "revision")
    list_filter = ("coverage_status", "surface")
    search_fields = ("technique_id", "name")
    filter_horizontal = ("tactics",)


class ChallengeEvidenceInline(admin.TabularInline):
    model = ChallengeEvidenceRequirement
    extra = 0
    autocomplete_fields = ("evidence",)


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = ("flag_id", "title", "outcome_id", "step", "difficulty", "points", "implemented")
    list_filter = ("implemented", "difficulty", "category")
    search_fields = ("flag_id", "title", "outcome_id")
    filter_horizontal = ("techniques",)
    inlines = (ChallengeEvidenceInline,)


@admin.register(ChallengeEvidenceRequirement)
class ChallengeEvidenceRequirementAdmin(admin.ModelAdmin):
    list_display = (
        "evidence_key",
        "challenge",
        "event_kind",
        "source_service",
        "freshness_seconds",
    )
    search_fields = ("evidence_key", "event_kind", "source_service", "source_asset")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("author", "object_type", "object_stable_id", "revision", "created_at")
    list_filter = ("object_type",)


@admin.register(Decision)
class DecisionAdmin(admin.ModelAdmin):
    list_display = ("decision", "object_type", "object_stable_id", "author", "created_at")
    list_filter = ("decision", "object_type")


@admin.register(ReviewState)
class ReviewStateAdmin(admin.ModelAdmin):
    list_display = ("object_type", "object_stable_id", "status", "revision", "updated_at")
    list_filter = ("status", "object_type")


@admin.register(ActivityEvent)
class ActivityEventAdmin(admin.ModelAdmin):
    list_display = ("verb", "actor", "scenario", "object_type", "object_stable_id", "created_at")
    list_filter = ("verb",)
