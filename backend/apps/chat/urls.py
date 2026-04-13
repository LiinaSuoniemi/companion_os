"""
Chat app — URL routes.

One route for now:
- /  → ChatView (GET loads the page, POST sends a message)
"""
from django.urls import path

from . import views

app_name = "chat"

urlpatterns = [
    path("", views.ChatView.as_view(), name="chat"),
    path("stream/", views.StreamView.as_view(), name="stream"),
    path("new/", views.NewConversationView.as_view(), name="new_conversation"),
]
