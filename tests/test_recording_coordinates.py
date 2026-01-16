from src.tools import recording


def test_build_gesture_params_sets_coordinate_space():
    params = recording._build_gesture_params(
        "tap",
        x=0.2,
        y=0.4,
        coordinate_space="normalized",
    )
    assert params["coordinate_space"] == "normalized"


def test_build_gesture_params_normalized_flag():
    params = recording._build_gesture_params(
        "tap",
        x=0.2,
        y=0.4,
        normalized=True,
    )
    assert params["coordinate_space"] == "normalized"


def test_apply_coordinate_space_scales_and_clamps():
    params = {
        "x": -0.2,
        "y": 1.2,
        "coordinate_space": "normalized",
    }
    scaled = recording._apply_coordinate_space(params, (100, 200))
    assert scaled["x"] == 0
    assert scaled["y"] == 199
