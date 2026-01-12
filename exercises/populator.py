"""Abstract interface for schema populators (adapters).

Schema populators are responsible for transforming domain-specific knowledge
(e.g., Chinese vocabulary and grammar) into generic exercise schemas.
This separates domain knowledge from exercise generation logic.
"""

from abc import ABC, abstractmethod

from models import KnowledgePoint

from .schemas import FillBlankSchema, MultipleChoiceSchema, ReorderSchema


class SchemaPopulator(ABC):
    """Abstract base class for domain-specific schema population.

    Subclasses implement domain knowledge (e.g., Chinese, Japanese)
    and populate the generic schemas declaratively. The schemas are
    then consumed by exercise generators to produce exercises.
    """

    @abstractmethod
    def populate_multiple_choice(
        self,
        knowledge_points: list[KnowledgePoint],
    ) -> MultipleChoiceSchema:
        """Populate multiple choice schema from knowledge points.

        Args:
            knowledge_points: All available knowledge points.

        Returns:
            A schema containing prompt types, prompt values, option types,
            and all possible options.
        """
        pass

    @abstractmethod
    def populate_fill_blank(
        self,
        knowledge_points: list[KnowledgePoint],
    ) -> FillBlankSchema:
        """Populate fill-blank schema from knowledge points.

        Args:
            knowledge_points: All available knowledge points.

        Returns:
            A schema containing templates, fills, option types, and options.
        """
        pass

    @abstractmethod
    def populate_reorder(
        self,
        knowledge_points: list[KnowledgePoint],
    ) -> ReorderSchema:
        """Populate reorder schema from knowledge points.

        Args:
            knowledge_points: All available knowledge points.

        Returns:
            A schema containing templates and slot fills.
        """
        pass
