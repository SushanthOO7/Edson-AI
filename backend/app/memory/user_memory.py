from dataclasses import dataclass


@dataclass(frozen=True)
class UserProfile:
    id: str
    name: str
    email: str
    role: str
    team: str
    signature: str


@dataclass(frozen=True)
class TeamProfile:
    id: str
    name: str
    rules: list[str]


class UserMemory:
    def get_current_user(self) -> UserProfile:
        return UserProfile(
            id="local-sushanth",
            name="Sushanth Vasudeva",
            email="sushanth@example.local",
            role="IT Helpdesk Assistant",
            team="Edson Info Systems",
            signature="Thanks,\nSushanth Vasudeva\nIT Helpdesk Assistant\nEdson Info Systems",
        )

    def get_current_team(self) -> TeamProfile:
        return TeamProfile(
            id="edson-info-systems",
            name="Edson Info Systems",
            rules=self.get_team_rules(),
        )

    def get_team_rules(self) -> list[str]:
        return [
            "Additional comments are customer-facing.",
            "Work notes are internal.",
            "Do not invent completed work.",
            "Short description should use CAMPUS_CODE - BUILDING_CODE - ROOM_NUMBER - Issue title when values are available.",
            "Build the issue title and description from More information.",
            "Do not use RITM/request metadata as the ticket description.",
            "Additional comments should usually ask for availability/date/time/location unless ticket activity explicitly supports a completion or closing comment.",
            "Work notes should be internal, factual, and based on More information and recent activity.",
        ]
