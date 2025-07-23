from dataclasses import dataclass

@dataclass
class User:
    _id: str = ""
    first_name: str = ""
    last_name: str = ""
    dob: str = ""
    phone: int = 12345678908

    def check_id(self, other) -> bool:
        return True if self._id == other._id else False
