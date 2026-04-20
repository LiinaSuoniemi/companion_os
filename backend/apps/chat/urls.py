"""
Chat app — URL routes.

Two entry points:
- /chat/          → conversation list (shows all past conversations)
- /chat/<id>/     → specific conversation (loads messages, allows chatting)
- /chat/<id>/stream/  → streaming endpoint for a specific conversation
- /chat/new/      → creates a new conversation and redirects to it
"""
from django.urls import path

from . import views

app_name = "chat"

urlpatterns = [
    path("", views.ConversationListView.as_view(), name="conversation_list"),
    path("<int:pk>/", views.ChatView.as_view(), name="chat"),
    path("<int:pk>/stream/", views.StreamView.as_view(), name="stream"),
    path("new/", views.NewConversationView.as_view(), name="new_conversation"),
    path("<int:pk>/rename/", views.RenameConversationView.as_view(), name="rename_conversation"),
    path("<int:pk>/delete/", views.DeleteConversationView.as_view(), name="delete_conversation"),
]
