from mcp_run import Client, ProfileSlug

import unittest
import os


class TestProfileSlug(unittest.TestCase):
    def test_user_and_name(self):
        slug = ProfileSlug.parse("aaa/bbb")
        self.assertEqual(slug.user, "aaa")
        self.assertEqual(slug.name, "bbb")
        self.assertEqual(slug, "aaa/bbb")

    def test_no_user(self):
        slug = ProfileSlug.parse("test")
        self.assertEqual(slug.user, "~")
        self.assertEqual(slug.name, "test")
        self.assertEqual(slug, "~/test")


class TestClient(unittest.TestCase):
    def client(self):
        try:
            client = Client()
            return client
        except Exception:
            self.skipTest("No client")

    def test_list_installs(self):
        client = self.client()
        installs = list(client.list_installs())
        i = client.installs.values()
        self.assertEqual(len(installs), len(i))
        for v in i:
            self.assertTrue(v.name != "")

    def test_search(self):
        client = self.client()
        res = list(client.search("fetch"))
        self.assertEqual(res[0].slug, "bhelx/fetch")

    def test_list_profiles(self):
        client = self.client()
        for profile in client.profiles[client.user.username].values():
            self.assertEqual(profile.slug.user, client.user.username)

    def test_call(self):
        client = self.client()
        results = client.call_tool("eval-js", params={"code": "'Hello, world!'"})
        for content in results.content:
            self.assertEqual(content.text, "Hello, world!")

    def test_profile_install_uninstall(self):
        client = self.client()
        profile = client.create_profile(
            "python-test-profile", description="this is a test", set_current=True
        )
        r = list(client.search("evaluate javascript"))
        client.install(r[0], name="evaljs")
        p = client.profiles["~"]["python-test-profile"]
        for install in p.list_installs():
            client.uninstall(install)
        client.delete_profile(profile)

    def test_tasks(self):
        client = self.client()

        if "ANTHROPIC_API_KEY" not in os.environ:
            self.skipTest("No Anthropic API key")

        my_task = client.create_task(
            "python-test-task",
            runner="anthropic",
            model="claude-3-5-sonnet-latest",
            prompt="write a greeting for {{ name }}",
        )

        # Run it
        task_run = my_task.run({"name": "World"})
        self.assertIn("World", task_run.results())

        # Retreive the task
        task = client.tasks["python-test-task"]
        self.assertEqual(my_task.task_slug, task.task_slug)

        # Run it again
        task_run = my_task.run({"name": "Bob"})
        self.assertIn("Bob", task_run.results())


if __name__ == "__main__":
    unittest.main()
