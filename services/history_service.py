import os
import pickle

CHAT_DIR = "chat_history_data"
os.makedirs(CHAT_DIR, exist_ok=True)


def save_chat_session(session_id: str, messages: list, last_context: dict):
    """Saves the current session messages and context to a local pickle file."""
    file_path = os.path.join(CHAT_DIR, f"{session_id}.pkl")
    with open(file_path, "wb") as f:
        pickle.dump({"messages": messages, "last_context": last_context}, f)


def load_chat_session(session_id: str):
    """Loads a specific chat session from a local pickle file."""
    file_path = os.path.join(CHAT_DIR, f"{session_id}.pkl")
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            return pickle.load(f)
    return None


def get_all_chat_sessions() -> list:
    """Retrieves all saved chat sessions sorted by most recent modification time."""
    sessions = []
    if not os.path.exists(CHAT_DIR):
        return sessions

    files = [f for f in os.listdir(CHAT_DIR) if f.endswith(".pkl")]
    files.sort(key=lambda x: os.path.getmtime(os.path.join(CHAT_DIR, x)), reverse=True)

    for f in files:
        sess_id = f.replace(".pkl", "")
        path = os.path.join(CHAT_DIR, f)
        title = "New Conversation"
        try:
            with open(path, "rb") as file:
                data = pickle.load(file)
                messages = data.get("messages", [])
                if messages:
                    for m in messages:
                        if m["role"] == "user":
                            title = m["content"][:28] + "..." if len(m["content"]) > 28 else m["content"]
                            break
        except Exception:
            pass
        sessions.append({"id": sess_id, "title": title})
    return sessions


def delete_chat_session(session_id: str):
    """Deletes a saved chat session file."""
    file_path = os.path.join(CHAT_DIR, f"{session_id}.pkl")
    if os.path.exists(file_path):
        os.remove(file_path)