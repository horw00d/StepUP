from callbacks.single_trial import register_single_trial_callbacks
from callbacks.cross_trial import register_cross_trial_callbacks
from callbacks.shared import register_shared_callbacks


def register_callbacks(app):
    register_single_trial_callbacks(app)
    register_cross_trial_callbacks(app)
    register_shared_callbacks(app)
