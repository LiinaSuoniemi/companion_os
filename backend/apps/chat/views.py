"""
Chat app — Views.

Three views:
- ChatView:            GET loads the page, POST sends a message (kept as fallback)
- StreamView:          POST saves user message, streams Claude response via SSE
- NewConversationView: POST creates a fresh conversation

Why keep the non-streaming POST at all?
As a fallback. If JavaScript is disabled or fails, the form still works.
Streaming is an enhancement on top of a working base.
"""
import hashlib
import json
import logging
import anthropic

logger = logging.getLogger(__name__)
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import StreamingHttpResponse
from django.shortcuts import render, redirect
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .models import Conversation, Message
from .prompts import detect_mode, get_system_prompt, CRISIS_KEYWORDS
from apps.safety.models import SafetyEvent

# Maximum message length — prevents context window abuse and protects API budget.
# 2000 characters is roughly 500 words. Enough for any real message.
# A user in crisis does not need to send an essay.
MAX_MESSAGE_LENGTH = 2000


def _log_crisis_event(user, message_text):
    """
    Create a SafetyEvent when crisis keywords are detected.

    Why hash the signal?
    We record that a crisis keyword was present — not what the user said.
    If this database is ever subpoenaed or breached, there is nothing here
    that identifies the content of the conversation. GDPR-safe by design.

    Tier 3 = immediate danger. Crisis keywords always map to the highest tier
    because we cannot distinguish severity from a keyword match alone.
    """
    signal_hash = hashlib.sha256(message_text.lower().encode()).hexdigest()
    SafetyEvent.objects.create(
        user=user,
        tier=3,
        signal_hash=signal_hash,
    )


@method_decorator(login_required, name="dispatch")
class ConversationListView(View):
    """
    Shows all conversations for the logged-in user.
    If no conversations exist, creates one and redirects to it.

    Why a list view?
    Conversation persistence means users need to see and select
    past conversations. This is the entry point to the chat.
    """
    template_name = "chat/conversation_list.html"

    def get(self, request):
        conversations = Conversation.objects.filter(user=request.user)
        if not conversations.exists():
            # First visit ever — create a conversation and go straight to it
            conversation = Conversation.objects.create(user=request.user)
            return redirect("chat:chat", pk=conversation.pk)

        # Check if ?list=1 is in the URL — user explicitly wants the full list
        if request.GET.get("list"):
            return render(request, self.template_name, {
                "conversations": conversations,
            })

        # Default: go straight to the most recent conversation
        return redirect("chat:chat", pk=conversations.first().pk)


@method_decorator(login_required, name="dispatch")
class NewConversationView(View):
    """
    Creates a fresh conversation and redirects to it.
    POST only — changing state should never be a GET request.
    """
    def post(self, request):
        conversation = Conversation.objects.create(user=request.user)
        return redirect("chat:chat", pk=conversation.pk)


@method_decorator(login_required, name="dispatch")
class RenameConversationView(View):
    """
    Renames a conversation. POST only.
    Only the owner can rename their own conversations.
    """
    def post(self, request, pk):
        try:
            conversation = Conversation.objects.get(pk=pk, user=request.user)
        except Conversation.DoesNotExist:
            return redirect("chat:conversation_list")

        title = request.POST.get("title", "").strip()[:100]
        conversation.title = title
        conversation.save(update_fields=["title"])

        # Return to wherever the user came from
        next_url = request.POST.get("next", "")
        if next_url:
            return redirect(next_url)
        return redirect("/chat/?list=1")


@method_decorator(login_required, name="dispatch")
class DeleteConversationView(View):
    """
    Permanently deletes a conversation and all its messages.
    POST only. Only the owner can delete their own conversations.

    Why permanent deletion?
    GDPR Article 17 — right to erasure. When a user deletes a conversation,
    it is gone. Not archived. Not soft-deleted. Gone from the database.
    Messages are CASCADE-deleted automatically because of the foreign key.
    """
    def post(self, request, pk):
        try:
            conversation = Conversation.objects.get(pk=pk, user=request.user)
        except Conversation.DoesNotExist:
            return redirect("chat:conversation_list")

        conversation.delete()
        return redirect("/chat/?list=1")


@method_decorator(login_required, name="dispatch")
class ChatView(View):
    """
    Main chat interface — now loads a SPECIFIC conversation by ID.
    GET: loads the page with that conversation's history.
    POST: non-streaming fallback (used if JS is disabled).

    Why by ID?
    Conversation persistence means every conversation has its own URL.
    /chat/5/ always loads conversation 5. Refreshing the page keeps you
    in the same conversation. Bookmarking works. Back button works.
    """

    template_name = "chat/chat.html"

    def get_conversation(self, user, pk):
        """
        Get a specific conversation that belongs to this user.
        Returns None if the conversation does not exist or belongs to someone else.
        """
        try:
            return Conversation.objects.get(pk=pk, user=user)
        except Conversation.DoesNotExist:
            return None

    def get(self, request, pk):
        conversation = self.get_conversation(request.user, pk)
        if not conversation:
            return redirect("chat:conversation_list")
        messages = conversation.messages.all()
        # Pass recent conversations for the dropdown in the top bar.
        # Limit to 10 most recent — the "View all" link goes to the full list.
        user_conversations = Conversation.objects.filter(
            user=request.user
        )[:10]
        return render(request, self.template_name, {
            "conversation": conversation,
            "messages": messages,
            "user_conversations": user_conversations,
        })

    def post(self, request, pk):
        """Non-streaming fallback — only used if JavaScript is disabled."""
        user_input = request.POST.get("message", "").strip()
        if not user_input:
            return redirect("chat:chat", pk=pk)

        conversation = self.get_conversation(request.user, pk)
        if not conversation:
            return redirect("chat:conversation_list")

        new_mode = detect_mode(user_input, conversation.active_mode)
        if new_mode != conversation.active_mode:
            conversation.active_mode = new_mode
            conversation.save()

        # Log crisis event if crisis keywords were detected.
        message_lower = user_input.lower()
        if any(kw in message_lower for kw in CRISIS_KEYWORDS):
            _log_crisis_event(request.user, user_input)

        Message.objects.create(
            conversation=conversation,
            role="user",
            content=user_input,
            active_mode=conversation.active_mode,
        )

        history = [
            {"role": msg.role, "content": msg.content}
            for msg in conversation.messages.all()
        ]

        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=get_system_prompt(conversation.active_mode),
            messages=history,
        )

        Message.objects.create(
            conversation=conversation,
            role="assistant",
            content=response.content[0].text,
            active_mode=conversation.active_mode,
        )

        return redirect("chat:chat", pk=pk)


@method_decorator(login_required, name="dispatch")
class StreamView(View):
    """
    Streaming endpoint — receives a message and streams Claude's response
    back to the browser using Server-Sent Events (SSE).

    Why SSE and not WebSockets?
    SSE is one-directional: server sends to client. That is exactly what we need.
    The user sends one message (via fetch POST), the server streams the response back.
    SSE works over regular HTTP. No extra infrastructure. Simpler and correct for this use case.

    How SSE works:
    The response Content-Type is text/event-stream.
    Each chunk is sent as: data: <json>\n\n
    The browser's EventSource API reads these chunks as they arrive.
    When the stream ends, we send a special done event.

    Flow:
    1. JS sends message via fetch POST to /chat/stream/
    2. This view saves the user message, starts Claude streaming
    3. Each token Claude generates is sent to the browser immediately
    4. When done, the full response is saved to the database
    5. JS assembles the tokens into the response bubble in real time
    """

    def get_conversation(self, user, pk):
        try:
            return Conversation.objects.get(pk=pk, user=user)
        except Conversation.DoesNotExist:
            return None

    def post(self, request, pk):
        try:
            body = json.loads(request.body)
            user_input = body.get("message", "").strip()
        except (json.JSONDecodeError, KeyError):
            user_input = ""

        if not user_input:
            return StreamingHttpResponse(
                self._error_stream("Empty message"),
                content_type="text/event-stream",
            )

        if len(user_input) > MAX_MESSAGE_LENGTH:
            return StreamingHttpResponse(
                self._error_stream("Message too long. Please keep messages under 2000 characters."),
                content_type="text/event-stream",
            )

        conversation = self.get_conversation(request.user, pk)
        if not conversation:
            return StreamingHttpResponse(
                self._error_stream("Conversation not found."),
                content_type="text/event-stream",
            )

        # Detect and update mode
        new_mode = detect_mode(user_input, conversation.active_mode)
        if new_mode != conversation.active_mode:
            conversation.active_mode = new_mode
            conversation.save()

        # Log crisis event if crisis keywords detected
        message_lower = user_input.lower()
        if any(kw in message_lower for kw in CRISIS_KEYWORDS):
            _log_crisis_event(request.user, user_input)

        # Save user message
        Message.objects.create(
            conversation=conversation,
            role="user",
            content=user_input,
            active_mode=conversation.active_mode,
        )

        # Build history for Claude
        history = [
            {"role": msg.role, "content": msg.content}
            for msg in conversation.messages.all()
        ]

        response = StreamingHttpResponse(
            self._stream_claude(conversation, history),
            content_type="text/event-stream",
        )
        # These headers keep the connection alive and prevent buffering
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response

    def _stream_claude(self, conversation, history):
        """
        Generator function — yields SSE chunks as Claude streams its response.

        Why a generator?
        Django's StreamingHttpResponse expects something it can iterate over.
        A generator yields one chunk at a time without loading everything into memory.
        Each yield sends that chunk to the browser immediately.
        """
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        full_response = []

        try:
            with client.messages.stream(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                system=get_system_prompt(conversation.active_mode),
                messages=history,
            ) as stream:
                for text in stream.text_stream:
                    full_response.append(text)
                    # Send each token as an SSE event
                    # json.dumps handles special characters safely
                    yield f"data: {json.dumps({'token': text})}\n\n"

            # Stream complete — save full response to database
            complete_text = "".join(full_response)
            Message.objects.create(
                conversation=conversation,
                role="assistant",
                content=complete_text,
                active_mode=conversation.active_mode,
            )

            # Send mode so the UI can update the mode badge
            yield f"data: {json.dumps({'done': True, 'mode': conversation.active_mode})}\n\n"

        except Exception:
            logger.exception("Claude streaming error in conversation %s", conversation.pk)
            yield f"data: {json.dumps({'error': 'Something went wrong. Please try again.'})}\n\n"

    def _error_stream(self, message):
        yield f"data: {json.dumps({'error': message})}\n\n"
