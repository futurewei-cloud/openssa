"""
=============================
ABSTRACT PROGRAMMER INTERFACE
=============================

`AbstractProgrammer` is `OpenSSA`'s abstract base class for using LMs to construct problem-solving Programs.
"""


from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from openssa.l2.util.lm.openai import OpenAILM

if TYPE_CHECKING:
    from openssa.l2.knowledge.abstract import Knowledge
    from openssa.l2.task import Task
    from openssa.l2.util.lm.abstract import AbstractLM
    from .program import AbstractProgram


@dataclass
class AbstractProgrammer(ABC):
    """Abstract Programmer."""

    # language model for generating problem-solving Programs
    lm: AbstractLM = field(default_factory=OpenAILM.from_defaults,
                           init=True,
                           repr=True,
                           hash=None,
                           compare=True,
                           metadata=None,
                           kw_only=False)

    @abstractmethod
    def construct_program(self, task: Task, knowledge: set[Knowledge] | None = None, **kwargs: Any) -> AbstractProgram:
        """Construct a Program for solving the posed Problem using given Knowledge & Resources."""