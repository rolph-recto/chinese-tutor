"""Chinese language adapter for exercise generation.

This module provides a high-level interface that wraps the declarative
schema populator and exercise generators. It maintains backward compatibility
with the original API while using the new architecture internally.
"""

from models import KnowledgePoint

from .chinese_populator import ChineseSchemaPopulator
from .config import ExerciseGeneratorConfig
from .generators import FillBlankGenerator, MultipleChoiceGenerator, ReorderGenerator
from .generic_models import (
    FillBlankExercise,
    MultipleChoiceExercise,
    ReorderExercise,
)


class ChineseExerciseAdapter:
    """Adapts Chinese knowledge points to generic exercises.

    This class provides a high-level interface for generating Chinese
    language exercises. It uses the declarative schema architecture
    internally while maintaining a simple API for callers.
    """

    def __init__(
        self,
        knowledge_points: list[KnowledgePoint],
        config: ExerciseGeneratorConfig | None = None,
    ):
        """Initialize the adapter.

        Args:
            knowledge_points: All available knowledge points.
            config: Optional configuration for exercise generation.
        """
        self.knowledge_points = knowledge_points
        self.config = config or ExerciseGeneratorConfig()

        # Populate schemas once using the declarative populator
        populator = ChineseSchemaPopulator()
        self._mc_schema = populator.populate_multiple_choice(knowledge_points)
        self._fb_schema = populator.populate_fill_blank(knowledge_points)
        self._reorder_schema = populator.populate_reorder(knowledge_points)

        # Create generators
        self._mc_generator = MultipleChoiceGenerator(
            self._mc_schema,
            self.config.multiple_choice,
        )
        self._fb_generator = FillBlankGenerator(
            self._fb_schema,
            self.config.fill_blank,
        )
        self._reorder_generator = ReorderGenerator(
            self._reorder_schema,
            self.config.reorder,
        )

        # Keep reference to vocab KPs for backward compatibility
        self.vocab_kps = [
            kp for kp in knowledge_points if kp.type.value == "vocabulary"
        ]
        self.kp_dict = {kp.id: kp for kp in knowledge_points}

    def create_chinese_to_english(
        self, target_kp: KnowledgePoint | None = None
    ) -> MultipleChoiceExercise | None:
        """Create a Chinese-to-English multiple choice exercise.

        Shows a Chinese word and asks for the English translation.

        Args:
            target_kp: If provided, create exercise for this knowledge point.

        Returns:
            A multiple choice exercise, or None if generation is not possible.
        """
        return self._mc_generator.generate(
            target_kp_id=target_kp.id if target_kp else None,
            prompt_type_id="chinese_to_english",
        )

    def create_english_to_chinese(
        self, target_kp: KnowledgePoint | None = None
    ) -> MultipleChoiceExercise | None:
        """Create an English-to-Chinese multiple choice exercise.

        Shows an English word and asks for the Chinese translation.

        Args:
            target_kp: If provided, create exercise for this knowledge point.

        Returns:
            A multiple choice exercise, or None if generation is not possible.
        """
        return self._mc_generator.generate(
            target_kp_id=target_kp.id if target_kp else None,
            prompt_type_id="english_to_chinese",
        )

    def create_minimal_pair(
        self, target_kp: KnowledgePoint | None = None
    ) -> MultipleChoiceExercise | None:
        """Create a minimal pair discrimination exercise.

        Shows an English definition and asks to select the correct Chinese character
        from visually/phonetically similar options.

        Args:
            target_kp: If provided, create exercise for this knowledge point.

        Returns:
            A multiple choice exercise, or None if generation is not possible.
        """
        return self._mc_generator.generate(
            target_kp_id=target_kp.id if target_kp else None,
            prompt_type_id="minimal_pair",
        )

    def create_cloze_deletion(
        self, target_kp: KnowledgePoint | None = None
    ) -> FillBlankExercise | None:
        """Create a cloze deletion exercise.

        Shows a Chinese sentence with a blank and asks to select the correct
        vocabulary word to fill it.

        Args:
            target_kp: If provided, create exercise for this knowledge point.

        Returns:
            A fill-blank exercise, or None if generation is not possible.
        """
        return self._fb_generator.generate(
            target_kp_id=target_kp.id if target_kp else None,
        )

    def create_segmented_translation(
        self, target_kp: KnowledgePoint | None = None
    ) -> ReorderExercise | None:
        """Create a segmented translation (reorder) exercise.

        Shows an English sentence and asks to arrange Chinese chunks
        in the correct order.

        Args:
            target_kp: If provided, prefer templates that use this knowledge point.

        Returns:
            A reorder exercise, or None if generation is not possible.
        """
        return self._reorder_generator.generate(
            target_kp_id=target_kp.id if target_kp else None,
        )
