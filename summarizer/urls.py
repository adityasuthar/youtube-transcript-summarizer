from django.urls import path
from .views import index, summarize_video

urlpatterns = [
    path('', index, name='index'),
    path('summarize/', summarize_video, name='summarize_video'),
]