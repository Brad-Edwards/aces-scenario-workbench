"""Domain model for the workbench.

Scenario content is organised as immutable revisions of ACES scenario packs.
Collaboration state (comments, decisions, review state, activity) anchors to the
tuple ``(revision, object_type, object_stable_id)`` so it never depends on YAML
line numbers or generated HTML positions.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models


class Role(models.TextChoices):
    AUTHOR = "author", "Author"
    REVIEWER = "reviewer", "Reviewer"
    STAKEHOLDER = "stakeholder", "Stakeholder"
    ADMINISTRATOR = "administrator", "Administrator"


class ObjectType(models.TextChoices):
    TACTIC = "tactic", "Tactic"
    STEP = "step", "Step"
    TECHNIQUE = "technique", "Technique"
    EVIDENCE = "evidence", "Evidence"
    CHALLENGE = "challenge", "Challenge"


class ReviewStatus(models.TextChoices):
    UNREVIEWED = "unreviewed", "Unreviewed"
    ACCEPTED = "accepted", "Accepted"
    NEEDS_CHANGE = "needs-change", "Needs change"
    RESOLVED = "resolved", "Resolved"


class DecisionType(models.TextChoices):
    ACCEPT = "accept", "Accept"
    NEEDS_CHANGE = "needs-change", "Needs change"
    RESOLVE = "resolve", "Resolve"
    REOPEN = "reopen", "Reopen"


class TimeStamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Scenario(TimeStamped):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL, through="Membership", related_name="scenarios"
    )

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Membership(TimeStamped):
    scenario = models.ForeignKey(Scenario, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.REVIEWER)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["scenario", "user"], name="unique_scenario_member"),
        ]
        ordering = ["scenario", "user"]

    def __str__(self) -> str:
        return f"{self.user} in {self.scenario} ({self.get_role_display()})"


class Revision(TimeStamped):
    """An immutable review bundle produced from a scenario pack."""

    scenario = models.ForeignKey(Scenario, on_delete=models.CASCADE, related_name="revisions")
    label = models.CharField(max_length=200)
    mapping_id = models.CharField(max_length=200, blank=True)
    pack_version = models.CharField(max_length=100, blank=True)
    source_repo = models.CharField(max_length=300, blank=True)
    source_commit = models.CharField(max_length=100, blank=True)
    content_digest = models.CharField(max_length=128)
    framework_name = models.CharField(max_length=100, blank=True)
    framework_release = models.CharField(max_length=50, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["scenario", "content_digest"], name="unique_revision_digest"
            ),
        ]
        ordering = ["scenario", "-created_at"]

    def __str__(self) -> str:
        return f"{self.scenario} @ {self.label}"


class Tactic(models.Model):
    revision = models.ForeignKey(Revision, on_delete=models.CASCADE, related_name="tactics")
    tactic_id = models.CharField(max_length=32)
    name = models.CharField(max_length=200)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["revision", "tactic_id"], name="unique_tactic"),
        ]
        ordering = ["revision", "tactic_id"]

    def __str__(self) -> str:
        return f"{self.tactic_id} {self.name}"


class Step(models.Model):
    revision = models.ForeignKey(Revision, on_delete=models.CASCADE, related_name="steps")
    path_step = models.CharField(max_length=16)
    behavior_specification = models.CharField(max_length=200, blank=True)
    tier = models.CharField(max_length=32, blank=True)
    surface = models.CharField(max_length=100, blank=True)
    estimated_minutes = models.PositiveIntegerField(null=True, blank=True)
    objective = models.TextField(blank=True)
    flag_outcome = models.CharField(max_length=100, blank=True)
    justification = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["revision", "path_step"], name="unique_step"),
        ]
        ordering = ["revision", "path_step"]

    def __str__(self) -> str:
        return f"Step {self.path_step}"


class Evidence(models.Model):
    revision = models.ForeignKey(Revision, on_delete=models.CASCADE, related_name="evidence")
    evidence_id = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["revision", "evidence_id"], name="unique_evidence"),
        ]
        ordering = ["revision", "evidence_id"]
        verbose_name_plural = "evidence"

    def __str__(self) -> str:
        return self.evidence_id


class Technique(models.Model):
    revision = models.ForeignKey(Revision, on_delete=models.CASCADE, related_name="techniques")
    technique_id = models.CharField(max_length=32)
    name = models.CharField(max_length=200)
    tactics = models.ManyToManyField(Tactic, related_name="techniques", blank=True)
    step = models.ForeignKey(
        Step, on_delete=models.SET_NULL, null=True, blank=True, related_name="techniques"
    )
    evidence = models.ForeignKey(
        Evidence, on_delete=models.SET_NULL, null=True, blank=True, related_name="techniques"
    )
    surface = models.CharField(max_length=100, blank=True)
    relationship = models.CharField(max_length=100, blank=True)
    coverage_status = models.CharField(max_length=50, blank=True)
    planned_action = models.TextField(blank=True)
    rationale = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["revision", "technique_id"], name="unique_technique"),
        ]
        ordering = ["revision", "technique_id"]

    @property
    def is_subtechnique(self) -> bool:
        # Legacy dotted identifiers distinguish sub-items by a second dot beyond
        # the one in the base id.
        return self.technique_id.count(".") > 1

    @property
    def parent_technique_id(self) -> str:
        if self.is_subtechnique:
            return self.technique_id.rsplit(".", 1)[0]
        return self.technique_id

    def __str__(self) -> str:
        return f"{self.technique_id} {self.name}"


class Challenge(models.Model):
    """A concrete participant-facing challenge derived from pack contracts."""

    revision = models.ForeignKey(Revision, on_delete=models.CASCADE, related_name="challenges")
    step = models.ForeignKey(
        Step, on_delete=models.SET_NULL, null=True, blank=True, related_name="challenges"
    )
    techniques = models.ManyToManyField(Technique, related_name="challenges", blank=True)
    flag_id = models.CharField(max_length=100)
    outcome_id = models.CharField(max_length=100)
    title = models.CharField(max_length=200)
    question = models.TextField(blank=True)
    category = models.CharField(max_length=100, blank=True)
    difficulty = models.CharField(max_length=50, blank=True)
    points = models.PositiveIntegerField(null=True, blank=True)
    hints = models.JSONField(default=list, blank=True)
    implemented = models.BooleanField(default=False)
    runtime_entrypoint = models.CharField(max_length=200, blank=True)
    source_path = models.CharField(max_length=300, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["revision", "flag_id"], name="unique_challenge"),
        ]
        ordering = ["revision", "flag_id"]

    def __str__(self) -> str:
        return self.title


class ChallengeEvidenceRequirement(models.Model):
    """Evidence a challenge requires before its receipt/award should count."""

    challenge = models.ForeignKey(
        Challenge, on_delete=models.CASCADE, related_name="evidence_requirements"
    )
    evidence = models.ForeignKey(
        Evidence,
        on_delete=models.CASCADE,
        related_name="challenge_requirements",
        null=True,
        blank=True,
    )
    evidence_key = models.CharField(max_length=100)
    predicate = models.TextField(blank=True)
    source_path = models.CharField(max_length=300, blank=True)
    event_id = models.CharField(max_length=100, blank=True)
    event_kind = models.CharField(max_length=100, blank=True)
    source_service = models.CharField(max_length=100, blank=True)
    source_asset = models.CharField(max_length=100, blank=True)
    freshness_seconds = models.PositiveIntegerField(null=True, blank=True)
    reset_owner = models.CharField(max_length=100, blank=True)
    fields = models.JSONField(default=list, blank=True)
    proof_fields = models.JSONField(default=list, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["challenge", "evidence_key"], name="unique_challenge_evidence"
            ),
        ]
        ordering = ["challenge", "evidence_key"]

    def __str__(self) -> str:
        return f"{self.challenge.flag_id} requires {self.evidence_key}"


class Comment(TimeStamped):
    revision = models.ForeignKey(Revision, on_delete=models.CASCADE, related_name="comments")
    object_type = models.CharField(max_length=20, choices=ObjectType.choices)
    object_stable_id = models.CharField(max_length=100)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comments"
    )
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies"
    )
    body = models.TextField()

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"Comment by {self.author} on {self.object_type}:{self.object_stable_id}"


class Decision(TimeStamped):
    revision = models.ForeignKey(Revision, on_delete=models.CASCADE, related_name="decisions")
    object_type = models.CharField(max_length=20, choices=ObjectType.choices)
    object_stable_id = models.CharField(max_length=100)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="decisions"
    )
    decision = models.CharField(max_length=20, choices=DecisionType.choices)
    rationale = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.get_decision_display()} on {self.object_type}:{self.object_stable_id}"


class ReviewState(TimeStamped):
    revision = models.ForeignKey(Revision, on_delete=models.CASCADE, related_name="review_states")
    object_type = models.CharField(max_length=20, choices=ObjectType.choices)
    object_stable_id = models.CharField(max_length=100)
    status = models.CharField(
        max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.UNREVIEWED
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="review_updates",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["revision", "object_type", "object_stable_id"],
                name="unique_review_state",
            ),
        ]
        ordering = ["revision", "object_type", "object_stable_id"]

    def __str__(self) -> str:
        return f"{self.object_type}:{self.object_stable_id} = {self.status}"


class ActivityEvent(models.Model):
    scenario = models.ForeignKey(Scenario, on_delete=models.CASCADE, related_name="activity")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activity",
    )
    verb = models.CharField(max_length=100)
    object_type = models.CharField(max_length=20, blank=True)
    object_stable_id = models.CharField(max_length=100, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.actor} {self.verb}"
