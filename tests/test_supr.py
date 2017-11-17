import mock
import json

import supr
from st2tests.base import BaseActionTestCase


class SuprTestCase(BaseActionTestCase):
    action_cls = supr.Supr

    class MockPostResponse:
        def __init__(self, content, status_code=200):
            self.content = content
            self.status_code = status_code

    def setUp(self):
        self.supr_base_url = "this-is-the-supr-base-url"
        self.api_user = "this-is-the-api-user"
        self.api_key = "this-is-the-api-key"
        self.project_to_email_dict = {
            "AA-0001": {"email": "this.is.a.pi@email.com", "sensitive": False},
            "BB-0002": {"email": "this.is.a.pi@email.com", "sensitive": True},
            "CC-0003": {"email": "this.is.a.pi@email.com,this.is.member.1@email.com", "sensitive": False},
            "DD-0004": {"email": "this.is.a.pi@email.com,this.is.member.1@email.com,this.is.member.2@email.com",
                        "sensitive": True}
        }
        self.expected_project_pi_ids = self.project_pi_ids()

    @staticmethod
    def mock_pi_id(**kwargs):
        # as a simple str->int conversion, just sum the ascii values for the characters in email
        return sum((ord(c) for c in kwargs["email"]))

    @staticmethod
    def post_mock_reponse(*args, **kwargs):
        return SuprTestCase.MockPostResponse(json.dumps(kwargs["data"]))

    def project_pi_ids(self):
        return {
            proj: map(
                lambda x: SuprTestCase.mock_pi_id(email=x),
                proj_info["email"].split(","))
            for proj, proj_info in self.project_to_email_dict.items()
        }

    def setup_and_run_create_delivery_project(self):
        project_names_and_ids = self.expected_project_pi_ids
        staging_info = {proj: {"size": 1e12} for proj in self.project_to_email_dict.keys()}
        project_info = dict(self.project_to_email_dict)
        return [
            supr.Supr.create_delivery_project(
                self.supr_base_url, project_names_and_ids, staging_info, project_info, self.api_user, self.api_key),
            project_names_and_ids,
            staging_info,
            project_info]

    def test_create_delivery_project(self):
        with mock.patch.object(
            supr.requests,
            'post',
            side_effect=SuprTestCase.post_mock_reponse
        ) as post_mock:
            observed_delivery_projects, project_names_and_ids, staging_info, project_info = \
                self.setup_and_run_create_delivery_project()
            self.assertListEqual(sorted(observed_delivery_projects.keys()), sorted(staging_info.keys()))
            for proj in project_names_and_ids.keys():
                observed_content = json.loads(observed_delivery_projects[proj])
                self.assertEqual(observed_content["pi_id"], project_names_and_ids[proj][0])
                self.assertListEqual(observed_content["member_ids"], project_names_and_ids[proj][1:])
                self.assertEqual(observed_content["ngi_sensitive_data"], project_info[proj]["sensitive"])

    def test_create_delivery_project_fail(self):
        with mock.patch.object(
            supr.requests,
            'post',
            return_value=SuprTestCase.MockPostResponse("some fail content", status_code=400)
        ) as post_mock:
            with self.assertRaises(AssertionError) as ae:
                self.setup_and_run_create_delivery_project()

    def test_search_for_pis(self):
        with mock.patch.object(
                supr.Supr, "search_by_email", side_effect=SuprTestCase.mock_pi_id) as search_mock:
            observed_pi_ids = supr.Supr.search_for_pis(
                self.project_to_email_dict,
                self.supr_base_url,
                self.api_user,
                self.api_key)
            self.assertDictEqual(observed_pi_ids, self.expected_project_pi_ids)
            self.assertEqual(
                search_mock.call_count,
                sum((len(values) for values in self.expected_project_pi_ids.values())))
            calls = [
                mock.call(base_url=self.supr_base_url, email=email, user=self.api_user, key=self.api_key)
                for project_info in self.project_to_email_dict.values()
                for email in project_info["email"].split(",")
            ]
            search_mock.assert_has_calls(calls, any_order=True)
