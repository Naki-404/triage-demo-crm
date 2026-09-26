from app.config import settings
from app.iin import InvalidIINError, generate_iin, needs_second_weights, validate_iin, with_wrong_check_digit


def test_valid_iin_first_weights():
    iin = generate_iin(second_weights=False)
    assert not needs_second_weights(iin[:11])
    validate_iin(iin)


def test_valid_iin_second_weights_clean():
    settings.CRM_MODE = "clean"
    settings.FAULT_IIN_SECOND_WEIGHTS = False
    iin = generate_iin(second_weights=True)
    assert needs_second_weights(iin[:11])
    validate_iin(iin)


def test_second_weights_rejected_in_experiment_fault():
    settings.CRM_MODE = "experiment"
    settings.FAULT_IIN_SECOND_WEIGHTS = True
    iin = generate_iin(second_weights=True)
    try:
        validate_iin(iin)
        assert False, "expected InvalidIINError"
    except InvalidIINError:
        pass
    finally:
        settings.CRM_MODE = "clean"
        settings.FAULT_IIN_SECOND_WEIGHTS = False


def test_wrong_check_digit():
    iin = with_wrong_check_digit(generate_iin())
    try:
        validate_iin(iin)
        assert False
    except InvalidIINError:
        pass


def test_fault_ignored_in_clean_mode():
    settings.CRM_MODE = "clean"
    settings.FAULT_IIN_SECOND_WEIGHTS = True
    iin = generate_iin(second_weights=True)
    validate_iin(iin)
    settings.FAULT_IIN_SECOND_WEIGHTS = False
