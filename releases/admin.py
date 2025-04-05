from django.contrib import admin
from django.http import HttpResponse
from django.template.loader import render_to_string

from .models import (
    FeatureRelease,
    PreRelease,
    Release,
    Releaser,
    SecurityIssue,
    SecurityIssueReleasesThrough,
    SecurityRelease,
)


def render_checklist(request, queryset):
    assert len(queryset) == 1, "A single item should be selected"
    [instance] = queryset
    context = {
        "instance": instance,
        "releaser": instance.releaser,
        "slug": instance.slug,
        "version": instance.version,
        "title": instance.__class__.__name__,
        **instance.__dict__,
    }
    if (release := getattr(instance, "release", None)) is not None:
        context["release"] = release
    if (data := getattr(instance, "get_context_data", None)) is not None:
        context.update(data)
    checklist = render_to_string(instance.checklist_template, context, request=request)
    return HttpResponse(checklist, content_type="text/markdown")


@admin.register(Release)
class ReleaseAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {"fields": ["version", "is_active", "is_lts"]}),
        ("Dates", {"fields": ["date", "eol_date"]}),
        ("Artifacts", {"fields": ["tarball", "wheel", "checksum"]}),
    ]
    list_display = (
        "version",
        "show_is_published",
        "is_lts",
        "date",
        "eol_date",
        "major",
        "minor",
        "micro",
        "show_status",
        "iteration",
    )
    list_filter = ("status", "is_lts", "is_active")
    ordering = ("-major", "-minor", "-micro", "-status", "-iteration")

    def get_form(self, request, obj=None, change=False, **kwargs):
        form_class = super().get_form(request, obj=obj, change=change, **kwargs)
        extensions = {"tarball": ".tar.gz", "wheel": ".whl", "checksum": ".asc,.txt"}
        for field, accept in extensions.items():
            widget = form_class.base_fields[field].widget
            widget.attrs.setdefault("accept", accept)
        return form_class

    @admin.display(
        description="status",
        ordering="status",
    )
    def show_status(self, obj):
        return obj.get_status_display()

    @admin.display(
        boolean=True,
        description="Published?",
        ordering="is_active",
    )
    def show_is_published(self, obj):
        return obj.is_published

    # Adding list_display and ordering from admin2.py, if needed.
    # If the admin1.py has all needed, then it is not required.
    # list_display = ["version", "date", "is_lts"]
    # ordering = ["-version"]

class ReleaserAdmin(admin.ModelAdmin):
    list_display = ["user", "key_id", "key_url"]

class ReleaseChecklistAdminMixin:
    list_display = ["version", "when", "releaser"]
    list_filter = ["releaser"]
    actions = ["render_checklist"]
    readonly_fields = ["blogpost_link"]

    def queryset(self, request):
        return super().get_queryset(request).select_related("release")

    @admin.action(description="Render checklists for selected releases")
    def render_checklist(self, request, queryset):
        return render_checklist(request, queryset)

class PreReleaseAdmin(ReleaseChecklistAdminMixin, admin.ModelAdmin):
    list_display = ["feature_release"] + ReleaseChecklistAdminMixin.list_display
    list_filter = ["feature_release"] + ReleaseChecklistAdminMixin.list_filter

class FeatureReleaseAdmin(ReleaseChecklistAdminMixin, admin.ModelAdmin):
    list_display = ReleaseChecklistAdminMixin.list_display + ["tagline"]

class SecurityReleaseAdmin(ReleaseChecklistAdminMixin, admin.ModelAdmin):
    list_display = ["versions", "when", "releaser"]
    search_fields = ["affected_branches"]
    ordering = ["-when"]
    readonly_fields = ["hashes_by_versions"]

class SecurityIssueAdmin(admin.ModelAdmin):
    list_display = ["cve_year_number", "summary", "severity", "commit_hash_main"]
    list_filter = ["severity", "release"]
    search_fields = ["cve_year_number", "summary", "description", "commit_hash_main"]
    ordering = ["-cve_year_number"]
    readonly_fields = ["hashes_by_branch", "releases"]

class SecurityIssueReleasesThroughAdmin(admin.ModelAdmin):
    list_display = ["security_issue_cve_year_number", "release_version", "commit_hash"]
    list_filter = ["release__version"]
    search_fields = [
        "security_issue__cve_year_number",  # Note: using the correct field name from the model.
        "release__version",
        "commit_hash",
    ]
    ordering = ["-security_issue__cve_year_number", "release__version"]

    @admin.display(
        description="CVE Year Number",
        ordering="security_issue__cve_year_number",
    )
    def security_issue_cve_year_number(self, obj):
        return obj.security_issue.cve_year_number if obj.security_issue else None

    @admin.display(
        description="Release Version",
        ordering="release__version",
    )
    def release_version(self, obj):
        return obj.release.version if obj.release else None


# Ensure each model is registered
admin.site.register(Releaser, ReleaserAdmin)
admin.site.register(FeatureRelease, FeatureReleaseAdmin)
admin.site.register(PreRelease, PreReleaseAdmin)
admin.site.register(SecurityRelease, SecurityReleaseAdmin)
admin.site.register(SecurityIssue, SecurityIssueAdmin)
admin.site.register(SecurityIssueReleasesThrough, SecurityIssueReleasesThroughAdmin)