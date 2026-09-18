from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    component: str
    status: str
    message: str
    details: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.status.upper() == "PASS"