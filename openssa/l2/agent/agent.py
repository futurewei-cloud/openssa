"""Agent with Planning, Reasoning & Informational Resources."""


from __future__ import annotations

from dataclasses import dataclass, field
from pprint import pformat
from typing import TYPE_CHECKING

from loguru import logger
from tqdm import tqdm

from openssa.l2.planning.hierarchical.planner import AutoHTPlanner
from openssa.l2.reasoning.ooda import OodaReasoner
from openssa.l2.task.status import TaskStatus
from openssa.l2.task.task import Task

if TYPE_CHECKING:
    from openssa.l2.planning.abstract.plan import APlan, AskAnsPair
    from openssa.l2.planning.abstract.planner import APlanner
    from openssa.l2.reasoning.abstract import AReasoner
    from openssa.l2.resource.abstract import AResource
    from openssa.l2.task.abstract import ATask


@dataclass
class Agent:
    """Agent with Planning, Reasoning & Informational Resources."""

    # Planner for decomposing tasks into executable solution Plans
    # using Automated Hierarchical Task Planner by default
    planner: APlanner | None = field(default_factory=AutoHTPlanner)

    # Reasoner for working through individual Tasks to either conclude or make partial progress on them
    # using OODA by default
    reasoner: AReasoner = field(default_factory=OodaReasoner)

    # set of Informational Resources for answering information-querying questions
    resources: set[AResource] = field(default_factory=set)

    # knowledge field added
    knowledge: set[str] = field(default_factory=set)

    @property
    def resource_overviews(self) -> dict[str, str]:
        """Overview available Informational Resources."""
        return {r.unique_name: r.overview for r in self.resources}


    def add_knowledge(self, new_knowledge: str | set[str]):
        """Add new knowledge to the agent"""
        if isinstance(new_knowledge, str):
            self.knowledge.add(new_knowledge)
        elif isinstance(new_knowledge, set[str]):
            self.knowledge.update(new_knowledge)
        else:
            raise ValueError("Input must be a string or a set of strings")

    def solve(self, problem: str, plan: APlan | None = None, dynamic: bool = True) -> str:
        """Solve posed Problem.

        Solution Plan can optionally be explicitly provided,
        or would be automatically generated by default if Planner is given.

        Solution Plan, whether explicitly provided or automatically generated,
        can be executed Dynamically (i.e., with as-needed further task decomposition)
        or Statically (i.e., literally per the Plan).
        """
        match (plan, self.planner, dynamic):

            # NO PLAN
            case (None, None, _):
                # if neither Plan nor Planner is given, directly use Reasoner
                result: str = self.reasoner.reason(task=Task(ask=problem, resources=self.resources), knowledge=self.knowledge)

            # AUTOMATED STATIC PLAN
            case (None, _, False) if self.planner:
                # if no Plan is given but Planner is, and if solving statically,
                # then use Planner to generate static Plan,
                # then execute such static Plan
                plan: APlan = self.planner.plan(problem=problem, resources=self.resources, knowledge=self.knowledge)

                logger.info(f'\n{pformat(object=plan.quick_repr,
                                         indent=2,
                                         width=120,
                                         depth=None,
                                         compact=False,
                                         sort_dicts=False,
                                         underscore_numbers=False)}')

                result: str = plan.execute(reasoner=self.reasoner, knowledge=self.knowledge)

            # AUTOMATED DYNAMIC PLAN
            case (None, _, True) if self.planner:
                # if no Plan is given but Planner is, and if solving dynamically,
                # then first directly use Reasoner,
                # and if that does not work, then use Planner to decompose 1 level more deeply,
                # and recurse until reaching confident solution or running out of depth
                result: str = self.solve_dynamically(problem=problem)

            # EXPERT-SPECIFIED STATIC PLAN
            case (_, None, _) if plan:
                # if Plan is given but no Planner is, then execute Plan statically
                logger.info(f'\n{pformat(object=plan.quick_repr,
                                         indent=2,
                                         width=120,
                                         depth=None,
                                         compact=False,
                                         sort_dicts=False,
                                         underscore_numbers=False)}')

                result: str = plan.execute(reasoner=self.reasoner, knowledge=self.knowledge)

            # EXPERT-SPECIFIED STATIC PLAN, with Resource updating
            case (_, _, False) if (plan and self.planner):
                # if both Plan and Planner are given, and if solving statically,
                # then use Planner to update Plan's resources,
                # then execute such updated static Plan
                plan: APlan = self.planner.update_plan_resources(plan, problem=problem, resources=self.resources, knowledge=self.knowledge)

                logger.info(f'\n{pformat(object=plan.quick_repr,
                                         indent=2,
                                         width=120,
                                         depth=None,
                                         compact=False,
                                         sort_dicts=False,
                                         underscore_numbers=False)}')

                result: str = plan.execute(reasoner=self.reasoner, knowledge=self.knowledge)

            # EXPERT-GUIDED DYNAMIC PLAN
            case (_, _, True) if (plan and self.planner):
                # if both Plan and Planner are given, and if solving dynamically,
                # TODO: dynamic solution
                raise NotImplementedError('Dynamic execution of given Plan and Planner not yet implemented')

            case _:
                raise ValueError('*** Invalid Plan-Planner-Dynamism Combination ***')

        return result

    def solve_dynamically(self, problem: str, planner: APlanner = None, other_results: list[AskAnsPair] | None = None) -> str:
        """Solve posed Problem dynamically.

        When first-pass result from Reasoner is unsatisfactory, decompose Problem and recursively solve decomposed Plan.
        """
        # attempt direct solution with Reasoner
        self.reasoner.reason(task := Task(ask=problem, resources=self.resources), knowledge=self.knowledge)

        # if Reasoner's result is unsatisfactory, and if Planner has not run out of allowed depth,
        # decompose Problem into 1-level Plan, and recursively solve such Plan with remaining allowed Planner depth
        if (task.status == TaskStatus.NEEDING_DECOMPOSITION) and (planner := planner or self.planner).max_depth:
            sub_planner: APlanner = planner.one_fewer_level_deep()

            sub_results: list[AskAnsPair] = []
            for sub_plan in tqdm((plan_1_level_deep := (planner.one_level_deep()
                                                        .plan(problem=problem, resources=self.resources))).sub_plans):
                sub_task: ATask = sub_plan.task
                sub_task.result: str = self.solve_dynamically(problem=sub_task.ask,
                                                              planner=sub_planner,
                                                              other_results=sub_results)
                sub_task.status: TaskStatus = TaskStatus.DONE
                sub_results.append((sub_task.ask, sub_task.result))

            task.result: str = plan_1_level_deep.execute(reasoner=self.reasoner, other_results=other_results, knowledge=self.knowledge)
            task.status: TaskStatus = TaskStatus.DONE

        return task.result
