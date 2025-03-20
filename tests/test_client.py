from mcp_run import Client, ClientConfig, ProfileSlug

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
            client = Client(profile=ProfileSlug("~", "default"))
            return client
        except Exception as exc:
            print(exc)
            self.skipTest("No client")

    def test_list_installs(self):
        client = self.client()
        installs = list(client.list_installs())
        # print(installs)
        i = client.installs.values()
        # print(list(i))
        self.assertEqual(len(installs), len(i))
        for v in i:
            self.assertTrue(v.name != "")

    def test_search(self):
        client = self.client()
        res = list(client.search("fetch"))
        self.assertEqual(res[0].slug, "dylibso/fetch")

    def test_list_profiles(self):
        client = self.client()
        for profile in client.profiles[client.user.username].values():
            self.assertEqual(profile.slug.user, client.user.username)

    def test_call(self):
        client = self.client()
        # print(list(client.tools.keys()))
        results = client.call_tool("eval-js", params={"code": "'Hello, world!'"})
        for content in results.content:
            self.assertEqual(content.text, "Hello, world!")
        results = client.call_tool("eval-js", params={"code": "'Hello, world!'"})
        for content in results.content:
            self.assertEqual(content.text, "Hello, world!")
        results = client.call_tool("gh-get-repo-contributors", params={"owner": "dylibso", "repo": "mcp-run-py"})
        for content in results.content:
            self.assertGreaterEqual(len(content.json), 1)
        results = client.call_tool("gh-get-repo-contributors", params={"owner": "dylibso", "repo": "mcp-run-py"})
        for content in results.content:
            self.assertGreaterEqual(len(content.json), 1)


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

        my_task = client.create_task(
            "python-test-task",
            provider="zshipko/openai_1",
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

        
    def test_tasks(self):
        client = self.client()

        for task in client.tasks:
            print(task)


if __name__ == "__main__":
    unittest.main()
