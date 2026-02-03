from django.views.generic import TemplateView


class Page(TemplateView):
    """
    Thin template-only views.
    - kwargs from URL (candidate_id, run_id) are automatically included in context.
    - extra_context is used to set `page` for the single page template.
    """
    pass


class LandingPageView(TemplateView):
    """Landing page view - public, no auth required"""
    template_name = "landing.html"

