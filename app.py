import streamlit as st
import anthropic
import os
import re
from dotenv import load_dotenv
from prompts import build_system_prompt

load_dotenv()


def get_api_key():
      try:
          return st.secrets["ANTHROPIC_API_KEY"]
      except Exception:
          return os.getenv("ANTHROPIC_API_KEY")


def extract_mode(text):
      """Pull {Mode Name} from the first line of a reply. Returns (mode_name, body)."""
      match = re.match(r'^\{([^}]+)\}\s*\n?', text.strip())
      if match:
          return match.group(1), text.strip()[match.end():]
      return None, text


  # --- Page config must be first Streamlit call ---
st.set_page_config(page_title="Companion OS", page_icon="🌿")

  # --- Password gate ---
if not st.session_state.get("authenticated"):
      st.title("🌿 Companion OS")
      st.caption("Enter your password to continue.")
      password = st.text_input("Password", type="password")
      if st.button("Enter"):
          try:
              correct = st.secrets["password"]
          except Exception:
              correct = os.getenv("APP_PASSWORD", "")
          if password == correct:
              st.session_state.authenticated = True
              st.rerun()
          else:
              st.error("Incorrect password.")
      st.stop()

  # --- Main app ---
st.title("🌿 Companion OS")
st.caption("12 modes — type what you need, or name a mode directly")

if "messages" not in st.session_state:
      st.session_state.messages = []

  # Render conversation history
for message in st.session_state.messages:
      with st.chat_message(message["role"]):
          if message["role"] == "assistant":
              mode_name, body = extract_mode(message["content"])
              if mode_name:
                  st.markdown(f"**[ {mode_name} ]**")
              st.markdown(body)
          else:
              st.markdown(message["content"])

  # Handle new input
if prompt := st.chat_input("What's happening right now?"):
      st.session_state.messages.append({"role": "user", "content": prompt})
      with st.chat_message("user"):
          st.markdown(prompt)

      client = anthropic.Anthropic(api_key=get_api_key())

      # Track active mode from last assistant response
      active_mode = None
      for m in reversed(st.session_state.messages):
          if m["role"] == "assistant":
              detected, _ = extract_mode(m["content"])
              if detected:
                  active_mode = detected
              break

      with st.chat_message("assistant"):
          badge_placeholder = st.empty()
          text_placeholder = st.empty()
          full_reply = ""

          with client.messages.stream(
              model="claude-sonnet-4-5",
              max_tokens=2048,
              system=build_system_prompt(active_mode=active_mode),
              messages=[
                  {"role": m["role"], "content": m["content"]}
                  for m in st.session_state.messages
              ],
          ) as stream:
              for chunk in stream.text_stream:
                  full_reply += chunk
                  text_placeholder.markdown(full_reply + "▌")

          mode_name, body = extract_mode(full_reply)
          if mode_name:
              badge_placeholder.markdown(f"**[ {mode_name} ]**")
          text_placeholder.markdown(body)

      # Store the full reply so Claude sees its own mode labels in future context
      st.session_state.messages.append({"role": "assistant", "content": full_reply})