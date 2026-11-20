from django.urls import path

from .views import (
    AIPredictionView,
    ChatListCreateView,
    JournalEntryListCreateView,
    JournalEntryRetrieveUpdateDestroyView,
    dashboard_view,
    refresh_stats_view,
    trading_stats_view,
    trading_summary_view,
)

urlpatterns = [
    # Journal entries CRUD
    path(
        "journal/entries/",
        JournalEntryListCreateView.as_view(),
        name="journal-list-create",
    ),
    path(
        "journal/entries/<int:pk>/",
        JournalEntryRetrieveUpdateDestroyView.as_view(),
        name="journal-detail",
    ),
    # Statistics and analytics
    path("journal/stats/", trading_stats_view, name="trading-stats"),
    path("journal/summary/", trading_summary_view, name="trading-summary"),
    path("journal/dashboard/", dashboard_view, name="trading-dashboard"),
    path("journal/refresh-stats/", refresh_stats_view, name="refresh-stats"),
    # AI Features
    path(
        "journal/entries/<int:pk>/predict/",
        AIPredictionView.as_view(),
        name="journal-predict",
    ),
    path(
        "journal/entries/<int:pk>/chat/",
        ChatListCreateView.as_view(),
        name="journal-chat",
    ),
]

# Main project urls.py should include:
# from django.contrib import admin
# from django.urls import path, include
#
# urlpatterns = [
#     path('admin/', admin.site.urls),
#     path('api/', include('journal.urls')),
# ]
