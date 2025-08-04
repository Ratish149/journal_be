
from django.urls import path
from .views import (
    JournalEntryListCreateView,
    JournalEntryRetrieveUpdateDestroyView,
    trading_stats_view,
    trading_summary_view,
    refresh_stats_view
)

urlpatterns = [
    # Journal entries CRUD
    path('journal/entries/', JournalEntryListCreateView.as_view(),
         name='journal-list-create'),
    path('journal/entries/<int:pk>/',
         JournalEntryRetrieveUpdateDestroyView.as_view(), name='journal-detail'),

    # Statistics and analytics
    path('journal/stats/', trading_stats_view, name='trading-stats'),
    path('journal/summary/', trading_summary_view, name='trading-summary'),
    path('journal/refresh-stats/', refresh_stats_view, name='refresh-stats'),
]

# Main project urls.py should include:
# from django.contrib import admin
# from django.urls import path, include
#
# urlpatterns = [
#     path('admin/', admin.site.urls),
#     path('api/', include('journal.urls')),
# ]
