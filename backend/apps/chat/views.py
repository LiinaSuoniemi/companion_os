"""
Chat app — Views.

The chat view does two things:
- GET:  load the current conversation and render the chat page
- POST: receive a message, call Claude, save both messages, return updated page

Why one view for both?
Because the chat page and the message sending are the same URL (/chat/).
GET loads the page. POST sends a message. This is standard Django form handling.

Why not a separate API endpoint (e.g. /api/chat/send/)?
We could — and we will when we add streaming. For now, a simple POST to the
same page keeps the code minimal and easy to follow. No JavaScript fetch needed yet.
"""
import anthropic
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils.decorators import method_decorator
from django.views import View

from .models import Conversation, Message
from .prompts import detect_mode, get_system_prompt


@method_decorator(login_required, name="dispatch")
class NewConversationView(View):
    """
    Creates a fresh conversation and redirects to chat.
    POST only — changing state should never be a GET request.
    """
    def post(self, request):
        Conversation.objects.create(user=request.user)
        return redirect("chat:chat")


@method_decorator(login_required, name="dispatch")
class ChatView(View):
    """
    Main chat interface.

    login_required: if the user is not logged in, redirect to login page.
    This is applied via decorator on the class, not on individual methods.
    """

    template_name = "chat/chat.html"

    def get_or_create_conversation(self, user):
        """
        Get the user's most recent conversation, or create a new one.

        Why not always create a new one?
        Because if the user refreshes the page, we don't want to lose their conversation.
        We keep one active conversation per user for now.
        Later: users can start new conversations or browse history.
        """
        conversation = Conversation.objects.filter(user=user).first()
        if not conversation:
            conversation = Conversation.objects.create(user=user)
        return conversation

    def get(self, request):
        conversation = self.get_or_create_conversation(request.user)
        messages = conversation.messages.all()
        return render(request, self.template_name, {
            "conversation": conversation,
            "messages": messages,
        })

    def post(self, request):
        user_input = request.POST.get("message", "").strip()

        # Ignore empty submissions
        if not user_input:
            return redirect("chat:chat")

        conversation = self.get_or_create_conversation(request.user)

        # Detect mode from the user's message
        # This updates the conversation mode if the message triggers a shift
        new_mode = detect_mode(user_input, conversation.active_mode)
        if new_mode != conversation.active_mode:
            conversation.active_mode = new_mode
            conversation.save()

        # Save the user's message to the database
        Message.objects.create(
            conversation=conversation,
            role="user",
            content=user_input,
            active_mode=conversation.active_mode,
        )

        # Build the message history to send to Claude
        # Claude needs the full conversation history so it has context
        # We load all messages and format them the way the Claude API expects
        history = [
            {"role": msg.role, "content": msg.content}
            for msg in conversation.messages.all()
        ]

        # Call Claude API
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=get_system_prompt(conversation.active_mode),
            messages=history,
        )

        assistant_reply = response.content[0].text

        # Save Claude's response to the database
        Message.objects.create(
            conversation=conversation,
            role="assistant",
            content=assistant_reply,
            active_mode=conversation.active_mode,
        )

        return redirect("chat:chat")

