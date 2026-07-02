from app.memory.user_memory import UserMemory, UserProfile


def get_current_user() -> UserProfile:
    return UserMemory().get_current_user()
