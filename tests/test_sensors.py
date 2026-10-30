import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SENSORS = ROOT / "sensors"
SETTINGS = ROOT / ".claude" / "settings.json"


def load(name):
    path = SENSORS / name / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def clean_env(**extra):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(extra)
    return env


def run_sensor(name, payload, env=None, cwd=None):
    return subprocess.run(
        [str(SENSORS / name / f"{name}.py")],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env or clean_env(),
        cwd=cwd or ROOT,
        timeout=30,
    )


def bash(command, cwd=None):
    payload = {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": command}}
    if cwd:
        payload["cwd"] = str(cwd)
    return payload


def git(repo, *args):
    subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *args],
        check=True,
        capture_output=True,
        env=clean_env(),
    )


def make_repo(directory, branch):
    git(directory, "init", "-q", "-b", branch)
    git(directory, "commit", "-q", "--allow-empty", "-m", "chore: init")
    return directory


def fake_gh(directory, stdout="", exit_code=0):
    bin_dir = Path(directory) / "bin"
    bin_dir.mkdir(exist_ok=True)
    (bin_dir / "out.json").write_text(stdout)
    script = bin_dir / "gh"
    script.write_text(f'#!/bin/sh\ncat "{bin_dir}/out.json"\nexit {exit_code}\n')
    script.chmod(0o755)
    return clean_env(PATH=f"{bin_dir}{os.pathsep}{os.environ['PATH']}")


class SharedHookTest(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, str(SENSORS / "_shared"))
        import hook

        self.hook = hook

    def test_segments_split_on_operators_outside_quotes_only(self):
        segments = list(self.hook.command_segments('git add a && git commit -m "fix: a; b | c" ; echo x & y | z', "."))
        self.assertEqual(
            [s.tokens for s in segments],
            [["git", "add", "a"], ["git", "commit", "-m", "fix: a; b | c"], ["echo", "x"], ["y"], ["z"]],
        )
        self.assertEqual([s.connector for s in segments], [None, "&&", ";", "&", "|"])

    def test_redirections_are_not_separators_or_arguments(self):
        segments = list(self.hook.command_segments("git push 2>&1 &> /dev/null >/tmp/o 1>&2 < in", "."))
        self.assertEqual([s.tokens for s in segments], [["git", "push"]])

    def test_cd_inside_a_subshell_does_not_leak(self):
        found = [(i.name, i.directory) for i in self.hook.git_invocations("(cd /x && git status); git push", "/r")]
        self.assertEqual(found, [("status", "/x"), ("push", "/r")])

    def test_command_v_runs_nothing(self):
        self.assertEqual(list(self.hook.git_invocations("command -v git push origin develop", "/r")), [])

    def test_tokenize_drops_one_level_of_quotes(self):
        self.assertEqual(
            self.hook.shell_tokens("git -c alias.x=\"commit --no-verify\" x 'a b'"),
            ["git", "-c", "alias.x=commit --no-verify", "x", "a b"],
        )

    def test_heredoc_bodies_are_stripped_and_returned(self):
        command = "cat > f.md <<'EOF'\ngit push origin develop\nEOF\necho ok"
        bodies = []
        self.assertNotIn("git push", self.hook.mark_heredocs(command, bodies))
        self.assertEqual(bodies, ["git push origin develop"])

    def test_here_string_is_not_a_heredoc(self):
        bodies = []
        self.hook.mark_heredocs("cat <<< EOF\nnext", bodies)
        self.assertEqual(bodies, [])

    def test_git_invocations_follow_cd_and_dash_c(self):
        invocations = list(self.hook.git_invocations("cd /a && git -C b commit -m x", "/start"))
        self.assertEqual([(i.name, i.directory) for i in invocations], [("commit", "/a/b")])

    def test_git_invocations_reach_into_shell_wrappers(self):
        invocations = list(self.hook.git_invocations("bash -c 'git push origin develop'", "/r"))
        self.assertEqual([(i.name, i.args) for i in invocations], [("push", ["origin", "develop"])])

    def test_wrappers_and_subshells_are_unwrapped(self):
        for command in [
            "command git push origin develop",
            "time -p git push origin develop",
            "nohup git push origin develop",
            "sudo -u me git push origin develop",
            "env -i FOO=1 git push origin develop",
            "nice -n 5 git push origin develop",
            "exec git push origin develop",
            "builtin git push origin develop",
            "(git push origin develop)",
            "{ git push origin develop; }",
            "echo $(git push origin develop)",
            'echo "$(git push origin develop)"',
            "echo `git push origin develop`",
            "true && (cd /x && git push origin develop)",
        ]:
            names = [(i.name, i.args[-1:]) for i in self.hook.git_invocations(command, "/r")]
            self.assertIn(("push", ["develop"]), names, command)

    def test_gh_global_flags_move_after_the_subcommand(self):
        found = [(c.args, c.directory) for c in self.hook.gh_invocations("command gh --repo o/r pr ready 43", "/r")]
        self.assertEqual(found, [(["pr", "ready", "43", "--repo", "o/r"], "/r")])
        self.assertEqual(list(self.hook.gh_invocations("gh -R o/r pr ready", "/r"))[0].args[:2], ["pr", "ready"])

    def test_heredocs_belong_to_their_own_segment(self):
        command = "cat > a <<'EOF'\nfirst\nEOF\ngit commit -F - <<'EOF'\nsecond\nEOF"
        commit = [i for i in self.hook.git_invocations(command, "/r") if i.name == "commit"][0]
        self.assertEqual(commit.heredocs, ["second"])

    def test_git_subprocess_ignores_inherited_git_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(Path(tmp), "develop")
            previous = os.environ.get("GIT_DIR")
            os.environ["GIT_DIR"] = "/nonexistent"
            try:
                self.assertEqual(self.hook.current_branch(str(repo)), "develop")
            finally:
                if previous is None:
                    del os.environ["GIT_DIR"]
                else:
                    os.environ["GIT_DIR"] = previous

    def test_render_fills_placeholders_and_falls_back_when_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            md = Path(tmp) / "x.md"
            md.write_text("got {{a}}")
            self.assertEqual(self.hook.render(md, {"a": "1"}), "got 1")
            self.assertIn("não pôde ser lida", self.hook.render(Path(tmp) / "missing.md", {}))


class CheckCommitConventionTest(unittest.TestCase):
    sensor = load("check-commit-convention")

    def subjects(self, command, cwd="/nonexistent"):
        return self.sensor.commit_subjects(command, cwd)

    def test_extracts_subject_from_each_message_form(self):
        self.assertEqual(self.subjects('git commit -m "feat: a" -m "body"'), ["feat: a"])
        self.assertEqual(self.subjects("git commit -am 'fix(infra): b'"), ["fix(infra): b"])
        self.assertEqual(self.subjects("git commit --message=chore:x"), ["chore:x"])
        heredoc = "git commit -m \"$(cat <<'EOF'\ndocs: c\n\nbody\nEOF\n)\""
        self.assertEqual(self.subjects(heredoc), ["docs: c"])
        self.assertEqual(self.subjects("git commit -F - <<EOF\n\ntest: d\nEOF"), ["test: d"])

    def test_unrelated_heredoc_before_the_commit_is_ignored(self):
        command = "cat > notes <<'EOF'\nnot a subject\nEOF\ngit commit -F - <<'EOF'\nfix: real\nEOF"
        self.assertEqual(self.subjects(command), ["fix: real"])
        self.assertEqual(self.subjects("env FOO=1 git commit -m 'bad'"), ["bad"])
        self.assertEqual(self.subjects("(git commit -m 'bad')"), ["bad"])

    def test_reads_message_file_relative_to_cwd(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "msg.txt").write_text("# comment\nci: e\n")
            self.assertEqual(self.subjects("git commit -F msg.txt", tmp), ["ci: e"])
            self.assertEqual(self.subjects(f"git commit --file={tmp}/msg.txt"), ["ci: e"])

    def test_ignores_commands_that_are_not_commits_or_carry_no_message(self):
        self.assertEqual(self.subjects('echo "git commit -m x"'), [])
        self.assertEqual(self.subjects("git commit --amend --no-edit"), [])
        self.assertEqual(self.subjects("git log -m"), [])

    def test_violation(self):
        ok = ["feat: a", "fix(compose): b", "refactor!: c", "chore(release): 1.2.0", "revert: x"]
        for subject in ok:
            self.assertEqual(self.sensor.violation(subject), "", subject)
        for subject in ["x", "Feat: a", "feat:a", "feature: a", "feat(Infra): a", "wip"]:
            self.assertIn("formato", self.sensor.violation(subject), subject)
        self.assertIn("73", self.sensor.violation("feat: " + "a" * 67))
        self.assertEqual(self.sensor.violation("feat: " + "a" * 66), "")

    def test_hook_blocks_bad_subject_and_allows_good_one(self):
        blocked = run_sensor("check-commit-convention", bash('git commit -m "ajusta coisa"'))
        self.assertEqual(blocked.returncode, 2)
        self.assertIn("ajusta coisa", blocked.stderr)
        self.assertEqual(run_sensor("check-commit-convention", bash('git commit -m "fix: a"')).returncode, 0)
        self.assertEqual(run_sensor("check-commit-convention", {}).returncode, 0)


class CheckBranchPrefixTest(unittest.TestCase):
    sensor = load("check-branch-prefix")

    def test_extracts_created_branch_from_every_creation_form(self):
        cases = {
            "git checkout -b feat/a": ["feat/a"],
            "git checkout -B 'fix/b' origin/develop": ["fix/b"],
            "git switch -c c": ["c"],
            "git switch --create d": ["d"],
            "git switch --create=e": ["e"],
            "git worktree add -b ci/f ../wt origin/develop": ["ci/f"],
            "git worktree add ../wt existing": [],
            "git worktree add ../new-wt": ["new-wt"],
            "git worktree add --detach ../wt": [],
            "git branch --copy old copied": ["copied"],
            "git branch -c copied2": ["copied2"],
            "command git switch -c wrapped": ["wrapped"],
            "git branch g": ["g"],
            "git branch -f h origin/x": ["h"],
            "git branch": [],
            "git branch -d old": [],
            "git branch -m old new": ["new"],
            "git branch -M renamed": ["renamed"],
            "git checkout -bjoined": ["joined"],
            "git switch -cjoined2": ["joined2"],
            "git worktree add -bjoined3 ../wt": ["joined3"],
            "git branch --show-current": [],
            "git switch develop": [],
            "git checkout -- file": [],
            "cat <<'EOF'\ngit checkout -b nope\nEOF": [],
        }
        for command, expected in cases.items():
            self.assertEqual(self.sensor.created_branches(command), expected, command)

    def test_conventional_names(self):
        allowed = [
            "feat/span-metrics", "fix/a1", "docs/readme", "ci/x", "perf/y", "test/z", "build/b",
            "style/s", "revert/r", "refactor/q", "chore/back-merge-v1-2-3", "release/1.2.3",
            "release/10.0.0", "develop", "main",
        ]
        for name in allowed:
            self.assertTrue(self.sensor.is_conventional(name), name)
        rejected = [
            "foo", "feature/x", "feat/Upper", "feat/-x", "feat/x-", "feat/a_b", "release/1.2",
            "release/v1.2.3", "release/01.2.3", "release/x", "feat/a/b",
        ]
        for name in rejected:
            self.assertFalse(self.sensor.is_conventional(name), name)

    def test_hook_exit_codes(self):
        self.assertEqual(run_sensor("check-branch-prefix", bash("git checkout -b foo")).returncode, 2)
        self.assertEqual(run_sensor("check-branch-prefix", bash("git switch -c release/1.0.0")).returncode, 0)


class BlockNoVerifyTest(unittest.TestCase):
    sensor = load("block-no-verify")

    def test_detects_bypasses(self):
        for command in [
            'git commit --no-verify -m "fix: a"',
            "git push --no-veri",
            "git commit -n -m x",
            "git commit -anm x",
            "git -c core.hooksPath=/dev/null commit -m x",
            "git config core.hooksPath /tmp",
            "GIT_CONFIG_VALUE_0=core.hooksPath git push",
            "bash -c 'git push --no-verify'",
            "env FOO=1 git push origin feat/x --no-verify",
            "git -c alias.c='commit --no-verify' c",
            "bash <<'EOF'\ngit commit --no-verify\nEOF",
            "(git commit --no-verify)",
            "time git push --no-verify",
            "git config core.hookspath /tmp",
            "git config CORE.HOOKSPATH /tmp",
        ]:
            self.assertIsNotNone(self.sensor.find_bypass(command), command)

    def test_message_value_is_not_read_as_a_flag(self):
        for command in ["git commit -m --no-verify", "git commit -F --no-verify", "git commit --message --no-verify"]:
            self.assertIsNone(self.sensor.find_bypass(command), command)

    def test_allows_normal_commands(self):
        for command in [
            "git commit -m 'fix: mention --no-verify in docs'",
            "git commit -m n",
            "git push origin feat/x",
            "git config --get core.hooksPath",
            "echo --no-verify",
            "cat > f <<'EOF'\ngit commit --no-verify\nEOF",
            "git log --no-walk",
        ]:
            self.assertIsNone(self.sensor.find_bypass(command), command)

    def test_hook_exit_codes(self):
        self.assertEqual(run_sensor("block-no-verify", bash("git push --no-verify")).returncode, 2)
        self.assertEqual(run_sensor("block-no-verify", bash("git push")).returncode, 0)


class BlockProtectedCommitTest(unittest.TestCase):
    sensor = load("block-protected-commit")

    def violation(self, command, branches):
        return self.sensor.violation_for(command, "/repo", lambda d: branches.get(d, "feat/x"))

    def test_blocks_commit_and_amend_on_protected(self):
        on_develop = {"/repo": "develop"}
        self.assertEqual(self.violation("git commit -m x", on_develop)["action"], "git commit")
        self.assertEqual(self.violation("git commit --amend", {"/repo": "main"})["branch"], "main")

    def test_switch_only_counts_when_chained_with_and(self):
        on_develop = {"/repo": "develop"}
        for command in [
            "git switch nonexistent; git commit -m x",
            "git switch feat/x || git commit -m x",
            "git switch feat/x & git commit -m x",
            "git switch feat/x\ngit commit -m x",
            "git switch feat/x | git commit -m x",
            "git switch -c feat/x && git add . ; git commit -m x",
            "if git switch feat/x; then git commit -m x; fi",
        ]:
            self.assertIsNotNone(self.violation(command, on_develop), command)
        for command in [
            "git switch -c feat/x && git commit -m x",
            "git switch -c feat/x && git add . && git commit -m x",
            "git switch feat/x && (git commit -m x)",
        ]:
            self.assertIsNone(self.violation(command, on_develop), command)
        self.assertIsNotNone(self.violation("git switch develop; git commit -m x", {}))

    def test_git_dir_and_work_tree_redirect_the_repository(self):
        branches = {"/repo": "feat/x", "/dev/.git": "develop", "/dev": "develop", "/feat/.git": "feat/x"}

        def resolve(location):
            return branches.get(location)

        def violation(command):
            return self.sensor.violation_for(command, "/repo", resolve)

        for command in [
            "git --git-dir=/dev/.git commit -m x",
            "git --git-dir /dev/.git commit -m x",
            "git -C / --git-dir=dev/.git commit -m x",
            "git --git-dir=/dev/.git --work-tree=/repo commit -m x",
            "GIT_DIR=/dev/.git git commit -m x",
            "env GIT_DIR=/dev/.git git commit -m x",
            "export GIT_DIR=/dev/.git; git commit -m x",
            "export GIT_DIR=/dev/.git && git commit -m x",
            "GIT_DIR=/dev/.git; git commit -m x",
            "git --git-dir=/missing/.git commit -m x",
            "GIT_DIR=/missing git commit -m x",
        ]:
            self.assertIsNotNone(violation(command), command)
        for command in [
            "git commit -m x",
            "git --git-dir=/feat/.git commit -m x",
            "git -C / --git-dir=feat/.git commit -m x",
            "cd / && GIT_DIR=feat/.git git commit -m x",
            "git --work-tree=/dev commit -m x",
            "(export GIT_DIR=/dev/.git); git commit -m x",
        ]:
            self.assertIsNone(violation(command), command)

    def test_checkout_of_an_existing_file_is_not_a_branch_switch(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "notes").write_text("x")
            found = self.sensor.violation_for("git checkout notes && git commit -m x", tmp, lambda d: "develop")
            self.assertIsNotNone(found)

    def test_amend_is_labelled(self):
        self.assertEqual(self.violation("git commit --amend --no-edit", {"/repo": "develop"})["action"], "git commit --amend")

    def test_follows_branch_switches_earlier_in_the_command(self):
        on_develop = {"/repo": "develop"}
        self.assertIsNone(self.violation("git switch -c feat/x && git commit -m x", on_develop))
        self.assertIsNone(self.violation("git checkout -b feat/x && git commit -m x", on_develop))
        self.assertIsNone(self.violation("git switch feat/x && git commit -m x", on_develop))
        self.assertIsNotNone(self.violation("git switch develop && git commit -m x", {}))
        self.assertIsNotNone(self.violation("git checkout -- f && git commit -m x", on_develop))
        self.assertIsNotNone(self.violation("sudo git commit -m x", on_develop))
        self.assertIsNotNone(self.violation("(git commit -m x)", on_develop))

    def test_allows_other_branches_and_other_actions(self):
        self.assertIsNone(self.violation("git commit -m x", {}))
        self.assertIsNone(self.violation("git reset HEAD~1", {"/repo": "develop"}))
        self.assertIsNone(self.violation("git reset --hard origin/develop", {"/repo": "develop"}))
        self.assertIsNone(self.violation("git status", {"/repo": "develop"}))

    def test_judges_the_checkout_the_command_names(self):
        branches = {"/repo": "feat/x", "/other": "develop"}
        self.assertIsNotNone(self.violation("cd /other && git commit -m x", branches))
        self.assertIsNotNone(self.violation("git -C /other commit -m x", branches))
        self.assertIsNone(self.violation("git -C /repo commit -m x", {"/other": "develop"}))

    def test_hook_against_real_repository(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(Path(tmp), "develop")
            self.assertEqual(run_sensor("block-protected-commit", bash("git commit -m 'fix: a'", repo)).returncode, 2)
            git(repo, "switch", "-q", "-c", "feat/x")
            self.assertEqual(run_sensor("block-protected-commit", bash("git commit -m 'fix: a'", repo)).returncode, 0)


class BlockProtectedPushTest(unittest.TestCase):
    sensor = load("block-protected-push")

    def target(self, command, current="feat/x"):
        return self.sensor.protected_target(command, "/repo", lambda d: current)

    def test_blocks_pushes_that_write_a_protected_branch(self):
        for command in [
            "git push origin develop",
            "git push origin main",
            "git push origin +develop",
            "git push origin refs/heads/main",
            "git push origin HEAD:develop",
            "git push origin feat/x:main",
            "git push origin develop:main",
            "git push origin :develop",
            "git push --delete origin main",
            "git push --all origin",
            "git -C /x push origin develop",
        ]:
            self.assertIsNotNone(self.target(command), command)

    def test_git_dir_redirects_the_implicit_push(self):
        branches = {"/r": "feat/x", "/dev/.git": "develop"}
        target = lambda command: self.sensor.protected_target(command, "/r", branches.get)  # noqa: E731
        self.assertIsNotNone(target("git --git-dir=/dev/.git push"))
        self.assertIsNotNone(target("GIT_DIR=/dev/.git git push origin HEAD"))
        self.assertIsNotNone(target("git --git-dir=/missing push"))
        self.assertIsNone(target("git --git-dir=/missing push origin feat/x"))
        self.assertIsNone(target("git push"))

    def test_redirections_and_indirect_arguments(self):
        self.assertIsNotNone(self.target("git push 2>&1", current="develop"))
        self.assertIsNotNone(self.target("git push > /tmp/o", current="develop"))
        self.assertIsNone(self.target("git push origin feat/x > /tmp/o 2>&1"))
        self.assertIsNotNone(self.target("echo develop | xargs git push origin"))
        self.assertIsNone(self.target("command -v git push origin develop"))

    def test_follows_branch_switches_and_wrappers(self):
        self.assertIsNotNone(self.target("git switch feat/x; git push", current="develop"))
        self.assertIsNotNone(self.target("git switch develop; git push", current="feat/x"))
        self.assertIsNone(self.target("git switch feat/x && git push", current="develop"))
        self.assertIsNotNone(self.target("git switch main && git push", current="feat/x"))
        self.assertIsNotNone(self.target("env git push origin develop"))
        self.assertIsNotNone(self.target("command git push origin develop"))
        self.assertIsNotNone(self.target("$(git push origin develop)"))

    def test_blocks_implicit_push_while_on_protected(self):
        for command in ["git push", "git push origin", "git push -u origin HEAD", "git push origin @"]:
            self.assertIsNotNone(self.target(command, current="develop"), command)

    def test_allows_task_branches_tags_and_reads_from_protected(self):
        for command in [
            "git push origin feat/x",
            "git push -u origin HEAD",
            "git push origin v1.2.0",
            "git push origin refs/tags/v1.2.0",
            "git push origin main:feat/x",
            "git push -o ci.skip origin feat/x",
        ]:
            self.assertIsNone(self.target(command), command)
        self.assertIsNone(self.target("git push origin v1.2.0", current="main"))
        self.assertIsNone(self.target("git push origin --tags", current="develop"))

    def test_hook_against_real_repository(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(Path(tmp), "main")
            self.assertEqual(run_sensor("block-protected-push", bash("git push", repo)).returncode, 2)
            self.assertEqual(run_sensor("block-protected-push", bash("git push origin v1.0.0", repo)).returncode, 0)


class RemindAdversarialVerificationTest(unittest.TestCase):
    sensor = load("remind-adversarial-verification")

    def test_detects_pr_creation_and_draft_flag(self):
        self.assertTrue(self.sensor.creates_pull_request("gh pr create --draft --title x"))
        self.assertFalse(self.sensor.creates_pull_request("echo gh pr create"))
        self.assertTrue(self.sensor.is_draft("gh pr create -d"))
        self.assertFalse(self.sensor.is_draft("gh pr create --title draft"))
        self.assertTrue(self.sensor.is_draft("gh pr create \\\n  --title x \\\n  --draft"))
        self.assertTrue(self.sensor.creates_pull_request("bash -c 'gh pr create --draft'"))
        self.assertFalse(self.sensor.creates_pull_request("cat > f <<'EOF'\ngh pr create\nEOF"))

    def test_push_branches(self):
        self.assertEqual(self.sensor.pushed_branches("git push -u origin feat/x", "/r", lambda d: "y"), [("feat/x", "/r")])
        self.assertEqual(self.sensor.pushed_branches("git push", "/r", lambda d: "fix/y"), [("fix/y", "/r")])
        self.assertEqual(self.sensor.pushed_branches("git push origin HEAD:feat/z", "/r", lambda d: "q"), [("feat/z", "/r")])
        self.assertEqual(self.sensor.pushed_branches("git push origin v1.0.0", "/r", lambda d: "main"), [])
        self.assertEqual(self.sensor.pushed_branches("git status", "/r", lambda d: "x"), [])

    def test_open_pull_request_lookup(self):
        found = self.sensor.open_pull_request("feat/x", "/r", lambda args, cwd: (0, '[{"number": 7}]'))
        self.assertEqual(found, 7)
        self.assertIsNone(self.sensor.open_pull_request("feat/x", "/r", lambda args, cwd: (0, "[]")))
        self.assertIsNone(self.sensor.open_pull_request("feat/x", "/r", lambda args, cwd: (1, "boom")))

    def test_hook_advises_and_never_blocks(self):
        created = run_sensor("remind-adversarial-verification", bash("gh pr create --title x"))
        self.assertEqual(created.returncode, 0)
        context = json.loads(created.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("--draft", context)
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "r"
            repo.mkdir()
            make_repo(repo, "feat/x")
            env = fake_gh(tmp, '[{"number": 42}]')
            pushed = run_sensor("remind-adversarial-verification", bash("git push", repo), env=env)
            self.assertEqual(pushed.returncode, 0)
            self.assertIn("#42", json.loads(pushed.stdout)["hookSpecificOutput"]["additionalContext"])
            env = fake_gh(tmp, "[]")
            silent = run_sensor("remind-adversarial-verification", bash("git push", repo), env=env)
            self.assertEqual((silent.returncode, silent.stdout), (0, ""))


class RequireAuditBeforeReadyTest(unittest.TestCase):
    sensor = load("require-audit-before-ready")
    HEAD = "0123456789abcdef0123456789abcdef01234567"

    def view(self, *bodies, head=None):
        payload = {"headRefOid": head or self.HEAD, "comments": [{"body": b} for b in bodies]}
        return lambda args, cwd: (0, json.dumps(payload))

    def test_ready_requests(self):
        self.assertEqual(self.sensor.ready_requests("gh pr ready 12", "/r"), [(["12"], "/r")])
        self.assertEqual(self.sensor.ready_requests("gh pr ready", "/r"), [([], "/r")])
        self.assertEqual(self.sensor.ready_requests("gh pr ready -R o/r 3", "/r"), [(["3", "-R", "o/r"], "/r")])
        self.assertEqual(self.sensor.ready_requests("cd /x && gh pr ready 1", "/r"), [(["1"], "/x")])
        self.assertEqual(self.sensor.ready_requests("gh pr ready 12 --undo", "/r"), [])
        self.assertEqual(self.sensor.ready_requests("gh pr view 12", "/r"), [])
        self.assertEqual(self.sensor.ready_requests("bash -c 'gh pr ready 41'", "/r"), [(["41"], "/r")])
        self.assertEqual(self.sensor.ready_requests("eval gh pr ready 7", "/r"), [(["7"], "/r")])

    def test_audit_status(self):
        status = self.sensor.audit_status
        self.assertEqual(status(self.HEAD, [f"audit: pass {self.HEAD}"]), "pass")
        self.assertEqual(status(self.HEAD, [f"## Audit\n\naudit: pass {self.HEAD}\nmore"]), "pass")
        self.assertIsNone(status(self.HEAD, ["audit: pass 0123456"]))
        self.assertIsNone(status(self.HEAD, [f"audit: pass {self.HEAD[:39]}"]))
        self.assertIsNone(status(self.HEAD, ["audit: pass fedcba9876"]))
        self.assertIsNone(status(self.HEAD, ["text audit: pass 0123456"]))
        self.assertEqual(status(self.HEAD, [f"audit: pass {self.HEAD}", f"audit: fail {self.HEAD}"]), "fail")
        self.assertEqual(status(self.HEAD, [f"audit: fail {self.HEAD}", f"audit: pass {self.HEAD}"]), "pass")
        self.assertIsNone(status(self.HEAD, []))

    def test_decide(self):
        decide = self.sensor.decide
        self.assertIsNone(decide("gh pr ready 1", "/r", self.view(f"audit: pass {self.HEAD}")))
        self.assertIsNotNone(decide("gh pr ready 1", "/r", self.view(f"audit: pass {self.HEAD[:12]}")))
        for wrapped in ["gh --repo o/r pr ready 43", "command gh pr ready 43", "time gh pr ready 43", "(gh pr ready 43)"]:
            self.assertIsNotNone(decide(wrapped, "/r", self.view()), wrapped)
        indirect = decide("echo 43 | xargs gh pr ready", "/r", self.view(f"audit: pass {self.HEAD}"))
        self.assertIn("xargs", indirect["reason"])
        self.assertIsNotNone(decide("gh pr ready 1", "/r", self.view("audit: pass deadbeef")))
        failed = decide("gh pr ready 1", "/r", self.view(f"audit: pass {self.HEAD}", f"audit: fail {self.HEAD}"))
        self.assertIn("fail", failed["reason"])
        self.assertIsNotNone(decide("bash -c 'gh pr ready 41'", "/r", self.view()))
        self.assertIsNotNone(decide("gh pr ready 1", "/r", self.view()))
        self.assertIsNone(decide("gh pr list", "/r", self.view()))
        failure = decide("gh pr ready 1", "/r", lambda args, cwd: (1, "HTTP 502"))
        self.assertIn("HTTP 502", failure["reason"])
        self.assertIsNotNone(decide("gh pr ready 1", "/r", lambda args, cwd: (0, "not json")))

    def test_old_gh_without_head_ref_oid_falls_back_to_last_commit(self):
        def old_gh(args, cwd):
            if "headRefOid,comments" in args:
                return 1, 'Unknown JSON field: "headRefOid"'
            payload = {"commits": [{"oid": "f" * 40}, {"oid": self.HEAD}], "comments": [{"body": f"audit: pass {self.HEAD}"}]}
            return 0, json.dumps(payload)

        self.assertIsNone(self.sensor.decide("gh pr ready 1", "/r", old_gh))

    def test_hook_uses_gh_from_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = {"headRefOid": self.HEAD, "comments": [{"body": f"audit: pass {self.HEAD}"}]}
            passed = run_sensor("require-audit-before-ready", bash("gh pr ready 5"), env=fake_gh(tmp, json.dumps(payload)))
            self.assertEqual(passed.returncode, 0, passed.stderr)
            payload["comments"] = []
            blocked = run_sensor("require-audit-before-ready", bash("gh pr ready 5"), env=fake_gh(tmp, json.dumps(payload)))
            self.assertEqual(blocked.returncode, 2)
            self.assertIn(self.HEAD, blocked.stderr)
            broken = run_sensor("require-audit-before-ready", bash("gh pr ready 5"), env=fake_gh(tmp, "", exit_code=1))
            self.assertEqual(broken.returncode, 2)


class RequireCommentBudgetTest(unittest.TestCase):
    sensor = load("require-comment-budget")

    def test_scope(self):
        for path in ["deploy/docker-compose.yml", "deploy/main.tf", "scripts/x.sh", "tests/t.py", "sensors/a/a.py", "src/a.yaml"]:
            self.assertTrue(self.sensor.applies_to(path), path)
        for path in ["README.md", "docs/a.md", "Makefile", ".github/workflows/ci.yml", "src/dev.env", "scriptsx/a.py"]:
            self.assertFalse(self.sensor.applies_to(path), path)

    def test_counts_only_added_lines(self):
        before = "a = 1\n# old comment\n"
        after = "a = 1\n# old comment\n# new one\nb = 2\n  // js style\n#!/usr/bin/env python3\n# noqa: E402\n\n"
        counts = self.sensor.count_added(before, after)
        self.assertEqual((counts.comments, counts.code), (2, 1))

    def test_reindenting_existing_lines_adds_nothing(self):
        counts = self.sensor.count_added("# note\nx = 1\n", "    # note\n    x = 1\n")
        self.assertEqual((counts.comments, counts.code), (0, 0))

    def test_flags_portuguese_comments(self):
        self.assertEqual(self.sensor.count_added("", "# configuração do coletor\nx = 1\n").portuguese, 1)
        self.assertEqual(self.sensor.count_added("", "# collector settings\nx = 1\n").portuguese, 0)

    def test_budget(self):
        over = self.sensor.over_budget
        self.assertFalse(over(self.sensor.Counts(1, 0, 0)))
        self.assertTrue(over(self.sensor.Counts(2, 30, 0)))
        self.assertFalse(over(self.sensor.Counts(2, 60, 0)))
        self.assertTrue(over(self.sensor.Counts(3, 60, 0)))

    def test_edited_texts(self):
        texts = self.sensor.edited_texts
        self.assertEqual(texts({"old_string": "a", "new_string": "b"}, lambda: "x"), ("a", "b"))
        self.assertEqual(texts({"edits": [{"old_string": "a", "new_string": "b"}, {"old_string": "c", "new_string": "d"}]}, lambda: "x"), ("a\nc", "b\nd"))
        self.assertEqual(texts({"content": "new"}, lambda: "head"), ("head", "new"))

    def test_hook_advises_without_blocking(self):
        payload = {
            "hook_event_name": "PostToolUse",
            "tool_name": "Edit",
            "tool_input": {
                "file_path": str(ROOT / "deploy" / "docker-compose.yml"),
                "old_string": "x: 1",
                "new_string": "# one\n# two\n# three\nx: 1",
            },
        }
        result = run_sensor("require-comment-budget", payload)
        self.assertEqual(result.returncode, 0)
        output = json.loads(result.stdout)["hookSpecificOutput"]
        self.assertEqual(output["hookEventName"], "PostToolUse")
        self.assertIn("deploy/docker-compose.yml", output["additionalContext"])
        payload["tool_input"]["new_string"] = "# configuração\n" + "x: 1\n" * 40
        portuguese = run_sensor("require-comment-budget", payload)
        self.assertIn("português", json.loads(portuguese.stdout)["hookSpecificOutput"]["additionalContext"])
        payload["tool_input"]["new_string"] = "# settings\n" + "x: 1\n" * 40
        self.assertEqual(run_sensor("require-comment-budget", payload).stdout, "")
        payload["tool_input"]["file_path"] = str(ROOT / "README.md")
        self.assertEqual(run_sensor("require-comment-budget", payload).stdout, "")


class RemindTaskRetroTest(unittest.TestCase):
    sensor = load("remind-task-retro")

    def test_readies(self):
        self.assertTrue(self.sensor.readies_pull_request("gh pr ready 3"))
        self.assertTrue(self.sensor.readies_pull_request("gh pr comment 3 --body-file f && gh pr ready 3"))
        self.assertFalse(self.sensor.readies_pull_request("gh pr ready 3 --undo"))
        self.assertFalse(self.sensor.readies_pull_request("echo 'gh pr ready'"))
        self.assertTrue(self.sensor.readies_pull_request("bash -c 'gh pr ready 41'"))

    def test_hook_advises(self):
        payload = dict(bash("gh pr ready 3"), hook_event_name="PostToolUse")
        result = run_sensor("remind-task-retro", payload)
        self.assertEqual(result.returncode, 0)
        output = json.loads(result.stdout)["hookSpecificOutput"]
        self.assertEqual(output["hookEventName"], "PostToolUse")
        self.assertIn("task-retro", output["additionalContext"])


class ShellContextPropertyTest(unittest.TestCase):
    """Every dangerous command must still be caught under any wrapper and any shell context."""

    WRAPPERS = [
        "", "env ", "env -i FOO=1 ", "FOO=1 ", "command ", "command -p ", "builtin ", "exec ", "time ", "time -p ",
        "nohup ", "sudo ", "sudo -u root ", "nice ", "nice -n 5 ", "ionice -c 3 ", "timeout 30 ",
        "timeout -s KILL 30 ", "timeout --preserve-status 5m ", "stdbuf -oL ", "stdbuf -o L -e 0 ", "xargs ",
        "xargs -n 1 ", "xargs -I {} ", "xargs -P 2 -L 1 ", "unbuffer ", "chronic ", "flock /tmp/lock ",
        "flock -w 5 /tmp/lock ", "watch -n 1 ", "nohup timeout 30 env FOO=1 ",
    ]
    CONTEXTS = [
        "{c}", "{c} 2>&1", "{c} &> /dev/null", "{c} > /tmp/o 2>&1", "true && {c}", "false || {c}", "true; {c}",
        "true\n{c}", "sleep 1 & {c}", "{c} &", "echo x | {c}", "{c} | cat", "echo x |& {c}", "! {c}", "({c})",
        "{{ {c}; }}", "echo $({c})", 'echo "$({c})"', "echo `{c}`", "if true; then {c}; fi", "if {c}; then :; fi",
        "if false; then :; elif true; then {c}; else :; fi", "while true; do {c}; done", "until false; do {c}; done",
        "for i in 1 2; do {c}; done", "case x in x) {c};; esac", "f() {{ {c}; }}; f", "bash -c '{c}'",
        'sh -c "{c}"', "eval '{c}'", "bash -c 'bash -c \"{c}\"'", "( if true; then ( {c} ); fi )",
        "time ( {c} )", "cd /tmp && ({c})",
    ]
    HEAD = "0123456789abcdef0123456789abcdef01234567"

    @staticmethod
    def on_develop_only_through_git_dir(location):
        return "develop" if location.startswith("/dev") else "feat/x"

    def cores(self):
        audit = load("require-audit-before-ready")
        push = load("block-protected-push")
        commit = load("block-protected-commit")
        no_verify = load("block-no-verify")
        prefix = load("check-branch-prefix")
        convention = load("check-commit-convention")
        no_audit = lambda args, cwd: (0, json.dumps({"headRefOid": self.HEAD, "comments": []}))  # noqa: E731
        return [
            ("gh pr ready 43", lambda cmd: audit.decide(cmd, "/r", no_audit) is not None),
            ("git push origin develop", lambda cmd: push.protected_target(cmd, "/r", lambda d: "feat/x") is not None),
            ("git commit -m x", lambda cmd: commit.violation_for(cmd, "/r", lambda d: "develop") is not None),
            ("git commit --no-verify -m x", lambda cmd: no_verify.find_bypass(cmd) is not None),
            (
                "git --git-dir=/dev/.git commit -m x",
                lambda cmd: commit.violation_for(cmd, "/r", self.on_develop_only_through_git_dir) is not None,
            ),
            (
                "GIT_DIR=/dev/.git git commit -m x",
                lambda cmd: commit.violation_for(cmd, "/r", self.on_develop_only_through_git_dir) is not None,
            ),
            (
                "git --git-dir /dev/.git push",
                lambda cmd: push.protected_target(cmd, "/r", self.on_develop_only_through_git_dir) is not None,
            ),
            ("git checkout -b foo", lambda cmd: "foo" in prefix.created_branches(cmd)),
            (
                "git commit -m ajusta",
                lambda cmd: any(convention.violation(s) for s in convention.commit_subjects(cmd, "/r")),
            ),
        ]

    def test_dangerous_commands_are_caught_everywhere(self):
        misses = []
        for core, caught in self.cores():
            for wrapper in self.WRAPPERS:
                for context in self.CONTEXTS:
                    command = context.format(c=wrapper + core)
                    if not caught(command):
                        misses.append(command)
        self.assertEqual(misses, [])

    def test_hooks_follow_git_dir_into_real_repositories(self):
        with tempfile.TemporaryDirectory() as tmp:
            dev = Path(tmp) / "dev"
            feat = Path(tmp) / "feat"
            dev.mkdir()
            feat.mkdir()
            make_repo(dev, "develop")
            make_repo(feat, "feat/x")
            message = "-m 'chore: x'"
            blocked = [
                ("block-protected-commit", f"git --git-dir={dev}/.git commit --allow-empty {message}"),
                ("block-protected-commit", f"git --git-dir {dev}/.git --work-tree {dev} commit {message}"),
                ("block-protected-commit", f"GIT_DIR={dev}/.git git commit {message}"),
                ("block-protected-commit", f"env GIT_DIR={dev}/.git git commit {message}"),
                ("block-protected-commit", f"export GIT_DIR={dev}/.git; git commit {message}"),
                ("block-protected-commit", f"git -C {tmp} --git-dir=dev/.git commit {message}"),
                ("block-protected-commit", f"git --git-dir={tmp}/missing/.git commit {message}"),
                ("block-protected-push", f"git --git-dir={dev}/.git push"),
                ("block-protected-push", f"GIT_DIR={dev}/.git git push origin HEAD"),
            ]
            for sensor, command in blocked:
                self.assertEqual(run_sensor(sensor, bash(command, feat)).returncode, 2, command)
            allowed = [
                ("block-protected-commit", f"git commit {message}"),
                ("block-protected-commit", f"git --git-dir={feat}/.git commit {message}"),
                ("block-protected-commit", f"git -C {tmp} --git-dir=feat/.git commit {message}"),
                ("block-protected-push", f"git --git-dir={feat}/.git push"),
            ]
            for sensor, command in allowed:
                self.assertEqual(run_sensor(sensor, bash(command, feat)).returncode, 0, command)

    def test_hooks_exit_2_for_the_audited_payloads(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "r"
            repo.mkdir()
            make_repo(repo, "develop")
            env = fake_gh(tmp, json.dumps({"headRefOid": self.HEAD, "comments": []}))
            cases = [
                ("require-audit-before-ready", "if true; then gh pr ready 43; fi"),
                ("require-audit-before-ready", "sleep 1 & gh pr ready 43"),
                ("require-audit-before-ready", "timeout 30 gh pr ready 43"),
                ("require-audit-before-ready", "echo 43 | xargs gh pr ready"),
                ("block-protected-push", "if true; then git push origin develop; fi"),
                ("block-protected-push", "sleep 1 & git push origin develop"),
                ("block-protected-push", "stdbuf -oL git push origin develop"),
                ("block-protected-commit", "while true; do git commit -m x; done"),
                ("block-protected-commit", "timeout 5 git commit -m x"),
                ("block-protected-commit", "git switch nonexistent; git commit -m x"),
                ("check-commit-convention", "sleep 1 & git commit -m ajusta"),
                ("check-branch-prefix", "if true; then git checkout -b foo; fi"),
                ("block-no-verify", "true & git commit --no-verify -m x"),
            ]
            for sensor, command in cases:
                result = run_sensor(sensor, bash(command, repo), env=env)
                self.assertEqual(result.returncode, 2, f"{sensor}: {command}")


class WiringTest(unittest.TestCase):
    EXPECTED = {
        "check-commit-convention": ("PreToolUse", "Bash"),
        "check-branch-prefix": ("PreToolUse", "Bash"),
        "block-no-verify": ("PreToolUse", "Bash"),
        "block-protected-commit": ("PreToolUse", "Bash"),
        "block-protected-push": ("PreToolUse", "Bash"),
        "remind-adversarial-verification": ("PreToolUse", "Bash"),
        "require-audit-before-ready": ("PreToolUse", "Bash"),
        "remind-task-retro": ("PostToolUse", "Bash"),
        "require-comment-budget": ("PostToolUse", "Edit|Write|MultiEdit"),
    }

    def wiring(self):
        hooks = json.loads(SETTINGS.read_text())["hooks"]
        return {
            (h["command"].rsplit("/", 1)[-1][: -len(".py")], event, group.get("matcher"))
            for event, groups in hooks.items()
            for group in groups
            for h in group["hooks"]
        }

    def test_each_sensor_is_wired_to_its_event_and_matcher(self):
        expected = {(name, event, matcher) for name, (event, matcher) in self.EXPECTED.items()}
        self.assertEqual(self.wiring(), expected)
        self.assertEqual(set(self.EXPECTED), {d.name for d in self.sensor_dirs()})

    def test_slow_gh_sensors_outlast_the_gh_timeout(self):
        hooks = json.loads(SETTINGS.read_text())["hooks"]
        timeouts = {
            h["command"].rsplit("/", 1)[-1]: h.get("timeout", 60)
            for groups in hooks.values()
            for group in groups
            for h in group["hooks"]
        }
        for name in ("remind-adversarial-verification.py", "require-audit-before-ready.py"):
            self.assertGreaterEqual(timeouts[name], 25, name)

    def wired_commands(self):
        hooks = json.loads(SETTINGS.read_text())["hooks"]
        return [h["command"] for groups in hooks.values() for group in groups for h in group["hooks"]]

    def sensor_dirs(self):
        return sorted(p for p in SENSORS.iterdir() if p.is_dir() and not p.name.startswith(("_", ".")))

    def test_every_wired_command_is_an_executable_sensor(self):
        prefix = '"$CLAUDE_PROJECT_DIR"/'
        for command in self.wired_commands():
            self.assertTrue(command.startswith(prefix), command)
            path = ROOT / command[len(prefix):]
            self.assertTrue(path.is_file(), command)
            self.assertTrue(path.stat().st_mode & stat.S_IXUSR, command)
            self.assertTrue(path.read_text().startswith("#!/usr/bin/env python3\n"), command)

    def test_every_sensor_is_wired_and_has_its_message(self):
        wired = "\n".join(self.wired_commands())
        for directory in self.sensor_dirs():
            name = directory.name
            self.assertIn(f"sensors/{name}/{name}.py", wired, name)
            self.assertTrue((directory / f"{name}.md").is_file(), name)

    def test_no_verify_is_denied(self):
        deny = json.loads(SETTINGS.read_text())["permissions"]["deny"]
        self.assertIn("Bash(git commit*--no-verify*)", deny)
        self.assertIn("Bash(git push*--no-verify*)", deny)

    def test_legacy_hooks_are_gone(self):
        self.assertFalse((ROOT / ".claude" / "hooks").exists())


if __name__ == "__main__":
    unittest.main()
