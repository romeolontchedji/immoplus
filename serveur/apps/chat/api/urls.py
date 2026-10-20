from django.urls import path

from . import views as v

urlpatterns = [
    path("conversations", v.Conversations.as_view(), name="conversations"),
    path("conversations/start", v.Demarrage.as_view(), name="conversation-start"),
    path(
        "conversations/<str:conversation_id>", v.ConversationDetail.as_view(), name="conversation"
    ),
    path(
        "conversations/<str:conversation_id>/messages",
        v.Messages.as_view(),
        name="conversation-messages",
    ),
    path("conversations/<str:conversation_id>/read", v.Lecture.as_view(), name="conversation-read"),
    path(
        "conversations/<str:conversation_id>/block", v.Blocage.as_view(), name="conversation-block"
    ),
    path(
        "conversations/<str:conversation_id>/unblock",
        v.Deblocage.as_view(),
        name="conversation-unblock",
    ),
    path("ws-ticket", v.TicketWebSocket.as_view(), name="ws-ticket"),
]
