import agent_eval_kit


def test_package_exposes_installed_version():
    assert agent_eval_kit.__version__ == "0.1.0"
