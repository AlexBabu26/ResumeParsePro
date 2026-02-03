"""
Candidate filters using django-filter for advanced filtering capabilities.
"""
from django_filters import rest_framework as filters
from .models import Candidate


class CandidateFilter(filters.FilterSet):
    """
    FilterSet for Candidate model with various filter options.
    
    Usage examples:
        /api/v1/candidates/?location=New%20York
        /api/v1/candidates/?seniority=Senior
        /api/v1/candidates/?min_conf=0.7&max_conf=1.0
        /api/v1/candidates/?created_after=2024-01-01
        /api/v1/candidates/?skills=Python,JavaScript
        /api/v1/candidates/?has_linkedin=true
    """
    # Text filters
    location = filters.CharFilter(field_name='location', lookup_expr='icontains')
    seniority = filters.CharFilter(field_name='seniority', lookup_expr='iexact')
    primary_role = filters.CharFilter(field_name='primary_role', lookup_expr='icontains')
    full_name = filters.CharFilter(field_name='full_name', lookup_expr='icontains')
    headline = filters.CharFilter(field_name='headline', lookup_expr='icontains')
    
    # Confidence filters
    min_conf = filters.NumberFilter(field_name='overall_confidence', lookup_expr='gte')
    max_conf = filters.NumberFilter(field_name='overall_confidence', lookup_expr='lte')
    
    # Date filters
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    # Related filters
    parse_run = filters.NumberFilter(field_name='parse_run_id')
    resume_document = filters.NumberFilter(field_name='resume_document_id')
    
    # Presence filters (check if field is not null/empty)
    has_linkedin = filters.BooleanFilter(method='filter_has_linkedin')
    has_github = filters.BooleanFilter(method='filter_has_github')
    has_portfolio = filters.BooleanFilter(method='filter_has_portfolio')
    has_email = filters.BooleanFilter(method='filter_has_email')
    has_phone = filters.BooleanFilter(method='filter_has_phone')
    
    # Skills filter (comma-separated)
    skills = filters.CharFilter(method='filter_skills')
    
    # All skills filter (must have ALL listed skills)
    all_skills = filters.CharFilter(method='filter_all_skills')
    
    # Education filters
    institution = filters.CharFilter(method='filter_institution')
    degree = filters.CharFilter(method='filter_degree')
    
    # Experience filters
    company = filters.CharFilter(method='filter_company')
    title = filters.CharFilter(method='filter_title')
    is_currently_employed = filters.BooleanFilter(method='filter_currently_employed')
    
    class Meta:
        model = Candidate
        fields = [
            'location', 'seniority', 'primary_role', 'full_name', 'headline',
            'min_conf', 'max_conf', 'created_after', 'created_before',
            'parse_run', 'resume_document',
            'has_linkedin', 'has_github', 'has_portfolio', 'has_email', 'has_phone',
            'skills', 'all_skills', 'institution', 'degree', 'company', 'title',
            'is_currently_employed',
        ]
    
    def filter_has_linkedin(self, queryset, name, value):
        if value is True:
            return queryset.exclude(linkedin__isnull=True).exclude(linkedin='')
        elif value is False:
            return queryset.filter(linkedin__isnull=True) | queryset.filter(linkedin='')
        return queryset
    
    def filter_has_github(self, queryset, name, value):
        if value is True:
            return queryset.exclude(github__isnull=True).exclude(github='')
        elif value is False:
            return queryset.filter(github__isnull=True) | queryset.filter(github='')
        return queryset
    
    def filter_has_portfolio(self, queryset, name, value):
        if value is True:
            return queryset.exclude(portfolio__isnull=True).exclude(portfolio='')
        elif value is False:
            return queryset.filter(portfolio__isnull=True) | queryset.filter(portfolio='')
        return queryset
    
    def filter_has_email(self, queryset, name, value):
        if value is True:
            return queryset.exclude(primary_email__isnull=True).exclude(primary_email='')
        elif value is False:
            return queryset.filter(primary_email__isnull=True) | queryset.filter(primary_email='')
        return queryset
    
    def filter_has_phone(self, queryset, name, value):
        if value is True:
            return queryset.exclude(primary_phone__isnull=True).exclude(primary_phone='')
        elif value is False:
            return queryset.filter(primary_phone__isnull=True) | queryset.filter(primary_phone='')
        return queryset
    
    def filter_skills(self, queryset, name, value):
        """
        Filter by skills - candidate must have AT LEAST ONE of the listed skills.
        Comma-separated: ?skills=Python,JavaScript
        """
        if not value:
            return queryset
        skill_list = [s.strip() for s in value.split(',') if s.strip()]
        if skill_list:
            return queryset.filter(skills__name__iexact__in=skill_list).distinct()
        return queryset
    
    def filter_all_skills(self, queryset, name, value):
        """
        Filter by skills - candidate must have ALL of the listed skills.
        Comma-separated: ?all_skills=Python,JavaScript
        """
        if not value:
            return queryset
        skill_list = [s.strip().lower() for s in value.split(',') if s.strip()]
        for skill in skill_list:
            queryset = queryset.filter(skills__name__iexact=skill)
        return queryset.distinct()
    
    def filter_institution(self, queryset, name, value):
        """Filter by education institution."""
        if not value:
            return queryset
        return queryset.filter(education__institution__icontains=value).distinct()
    
    def filter_degree(self, queryset, name, value):
        """Filter by education degree."""
        if not value:
            return queryset
        return queryset.filter(education__degree__icontains=value).distinct()
    
    def filter_company(self, queryset, name, value):
        """Filter by experience company."""
        if not value:
            return queryset
        return queryset.filter(experience__company__icontains=value).distinct()
    
    def filter_title(self, queryset, name, value):
        """Filter by job title."""
        if not value:
            return queryset
        return queryset.filter(experience__title__icontains=value).distinct()
    
    def filter_currently_employed(self, queryset, name, value):
        """Filter for candidates with current employment."""
        if value is True:
            return queryset.filter(experience__is_current=True).distinct()
        elif value is False:
            return queryset.exclude(experience__is_current=True).distinct()
        return queryset
