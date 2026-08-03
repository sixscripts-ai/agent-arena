from deepeval.metrics import AnswerRelevancyMetric
from deepeval.models import OpenRouterModel

_eval_model = OpenRouterModel(
    model="poolside/laguna-s-2.1:free",
    cost_per_input_token=0.0,
    cost_per_output_token=0.0,
)

SINGLE_TURN_NO_TRACING_METRICS = [
    AnswerRelevancyMetric(threshold=0.5, model=_eval_model),
]
