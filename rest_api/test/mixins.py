import json
import os
from urllib.parse import urlencode

from django.contrib.auth import models as django_models
from django.test import TestCase
from django.urls import reverse
from fastjsonschema import JsonSchemaException
from fastjsonschema import validate as json_validate
from rest_api import models
from rest_framework import status
from rest_framework.test import (
    APIRequestFactory,
    force_authenticate,
    APITransactionTestCase,
    APITestCase,
)


class FixtureModelTestCase(TestCase):
    fixtures = [
        "initial_auth",
        "test_data",
    ]
    model = None
    obj = None

    def get_object(self, *args):
        if self.obj is None and self.model is not None:
            self.obj = self.model.objects.first()
        return self.obj


class FixtureApiMixin(object):
    def get_request_user(self, *args):
        if self.request_user_name is None:
            self.request_user_name = "request_user"
        return django_models.User.objects.get(username=self.request_user_name)

    def get_user(self, username, password=None, *args):
        user = self.usermap.get(username)
        if user is None:
            try:
                user = django_models.User.objects.get(username=username)
            except django_models.User.DoesNotExist:
                print(
                    f"Users: {', '.join(map(lambda u: u.username, django_models.User.objects.all()))}"
                )
                self.fail(f"no user found with username {username}")

            self.usermap[username] = user
        if password is not None:
            user.set_password(password)
            user.save()
        return user


class FixtureAPITestCase(APITestCase, FixtureApiMixin):
    fixtures = ["initial_auth", "test_data"]

    factory = APIRequestFactory()
    request_user_name = None
    usermap = dict()


class FixtureAPITransactionTestCase(APITransactionTestCase, FixtureApiMixin):
    fixtures = ["initial_auth", "test_data"]

    factory = APIRequestFactory()
    request_user_name = None
    usermap = dict()


class CustomTestMixin:
    model = None
    viewset = None
    arguments = {}
    reverse_urls = []

    def test_reverse_url_lookup(self, *args):
        for name, args, url in self.reverse_urls:
            self.assertEqual(reverse(name, args=args), url)

    def get_instance_or_none(self, pk, *args):
        try:
            return self.model.objects.get(pk=pk)
        except self.model.DoesNotExist:
            return None


class ListViewSetTestMixin(CustomTestMixin):
    expected_list_count = 0

    def get_list_response(self, parameter, *args):
        view = self.viewset.as_view({"get": "list"})

        request = self.factory.get(parameter)
        force_authenticate(request, user=self.get_request_user())
        return view(request, **self.arguments)

    def test_list(self, *args):
        response = self.get_list_response("")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # count based on fixtures/test_data
        self.assertEqual(response.data["count"], self.expected_list_count)

    def _test_list_filtering(self, filter, *args):
        response = self.get_list_response(f"?{filter}")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertIn("count", response.data)
        count = (int)(response.data["count"])
        self.assertLess(count, self.expected_list_count)


class RetrieveViewSetTestMixin(CustomTestMixin):
    pk_name = "id"

    def get_instance_and_lookup_field(self, pk=None, *args):
        if pk is not None:
            instance = self.model.objects.get(pk=pk)
        else:
            instance = self.model.objects.first()
        lookup_field = {
            self.viewset.lookup_field: instance.serializable_value(
                self.viewset.lookup_field
            )
        }
        return instance, lookup_field

    def test_retrieve(self, *args):
        self._test_retrieve()

    def _test_retrieve(self, pk=None, *args, **kwargs):
        view = self.viewset.as_view({"get": "retrieve"})

        instance, lookup_field = self.get_instance_and_lookup_field(pk=pk)
        request = self.factory.get("")
        force_authenticate(request, user=self.get_request_user())
        response = view(request, **lookup_field, **kwargs)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(self.pk_name, response.data, response.data)
        self.assertEqual(response.data[self.pk_name], instance.pk, response.data)


class UpdateViewSetTestMixin(RetrieveViewSetTestMixin):
    def _test_update(self, name, filename, pk=None, url="", *args):
        with open(filename, mode="r") as f:
            params = json.loads(f.read())
        if not params.get("filters") or not params.get("data"):
            self.fail(f"File {filename} needs filters and data to test update.")
        filters = params.get("filters")
        data = params.get("data")
        if pk == None:
            if "pk" in filters:
                pk = filters["pk"]
            elif "id" in filters:
                pk = filters["id"]
        view = self.viewset.as_view({"patch": "partial_update"})
        request = self.factory.patch(
            f"{url}?{urlencode(filters)}", data=data, format="json"
        )

        force_authenticate(request, user=self.get_request_user())
        response = view(request, pk=pk)
        response.render()
        responseJSON = json.loads(response.content)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        for key in filters:
            self.assertIn(key, responseJSON)
            self.assertEqual(responseJSON[key], filters[key])
        for key in data:
            if key == "version" or key == "change_reason":
                continue
            self.assertIn(key, responseJSON)
            self.assertEqual(responseJSON[key], data[key])
            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def _test_update_error_examples(self, name, filename, pk=None, *args):
        with open(filename, mode="r") as f:
            test_content = json.loads(f.read())
        if not test_content["params"]["filters"] or not test_content["params"]["data"]:
            self.fail(f"File {filename} needs filters and data to test update.")
        filters = test_content["params"]["filters"]
        data = test_content["params"]["data"]
        if pk == None:
            if "pk" in filters:
                pk = filters["pk"]
            elif "id" in filters:
                pk = filters["id"]
        view = self.viewset.as_view({"patch": "partial_update"})
        request = self.factory.patch(f"?{urlencode(filters)}", data=data, format="json")

        force_authenticate(request, user=self.get_request_user())
        response = view(request, pk=pk)
        response.render()
        responseJSON = json.loads(response.content)
        error_example = test_content["expected_response"]
        self.assertEqual(
            response.status_code,
            error_example["expected_status_code"],
            msg=response.data,
        )
        if "expected_response_data" in error_example:
            self.assertDictEqual(responseJSON, error_example["expected_response_data"])
        if "expected_response_schema" in error_example:
            try:
                json_validate(error_example["expected_response_schema"], responseJSON)
            except JsonSchemaException as e:
                self.fail(e)


class DestroyViewSetTestMixin(CustomTestMixin):
    def test_destroy(self, *args):
        self._test_destroy("", 1)

    def _test_destroy(self, name, pk, username=None, *args):
        view = self.viewset.as_view({"delete": "destroy"})
        instance, lookup_field = self.get_instance_and_lookup_field(pk=pk)

        request = self.factory.delete("", format="json")
        if username is None:
            force_authenticate(request, user=self.get_request_user())
        else:
            force_authenticate(request, user=self.get_user(username))
        response = view(request, **lookup_field)
        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT, response.data
        )
        instance = self.get_instance_or_none(pk)
        self.assertIsNone(instance)


class CreateViewSetTestMixin(CustomTestMixin):
    def _test_create(self, _, filename, url="", *args):
        view = self.viewset.as_view({"post": "create"})
        with open(filename, mode="r") as f:
            data = json.loads(f.read())
        request = self.factory.post(url, data=data, format="json")
        force_authenticate(request, user=self.get_request_user())

        objects_before = self.model.objects.count()
        response = view(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(objects_before + 1, self.model.objects.count())

    def _test_error_examples(self, _, filename, *args, action="create", pk=None):
        view = self.viewset.as_view({"post": action})
        with open(filename, mode="r") as f:
            error_example = json.loads(f.read())
        request = self.factory.post("", data=error_example["data"], format="json")
        force_authenticate(request, user=self.get_request_user())
        response = view(request, pk=pk)
        self.assertEqual(
            response.status_code,
            error_example["expected_status_code"],
            msg=response.data,
        )
        if "expected_response_data" in error_example:
            self.assertDictEqual(response.data, error_example["expected_response_data"])
        if "expected_response_schema" in error_example:
            try:
                json_validate(error_example["expected_response_schema"], response.data)
            except JsonSchemaException as e:
                self.fail(e)


class ListSchemaTestMixin(CustomTestMixin):
    def _test_list_schema(self, schema_file_prefix, version, *args):
        schema_file = os.path.join(
            "transfer-protocol", "schemata", f"{schema_file_prefix}_v{version}.json"
        )
        view = self.viewset.as_view({"get": "list"})
        request = self.factory.get(
            "", HTTP_ACCEPT=f"application/json; version={version}"
        )
        force_authenticate(request, user=self.get_request_user())

        response = view(request, **self.arguments)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        with open(schema_file, mode="r") as f:
            json_schema = json.loads(f.read())

        try:
            json_validate(json_schema, response.data)
        except JsonSchemaException as e:
            self.fail(f"{e}: {response.data}")


class OrderingTestMixin(CustomTestMixin):
    def _test_list_ordering(self, orderingfield, *args):
        view = self.viewset.as_view({"get": "list"})
        request_asc = self.factory.get(f"?ordering={orderingfield}")
        request_desc = self.factory.get(f"?ordering=-{orderingfield}")
        force_authenticate(request_asc, user=self.get_request_user())
        force_authenticate(request_desc, user=self.get_request_user())
        response_asc = view(request_asc, **self.arguments)
        response_desc = view(request_desc, **self.arguments)
        self.assertEqual(
            response_asc.status_code, status.HTTP_200_OK, response_asc.data
        )
        self.assertEqual(
            response_desc.status_code, status.HTTP_200_OK, response_desc.data
        )
        self.assertIn("count", response_asc.data, response_asc.data)
        if response_asc.data["count"] < 2:
            self.skipTest("Not enough objects in test_data")
        else:
            self.assertIn("results", response_asc.data, response_asc.data)
            self.assertIn("results", response_desc.data, response_desc.data)
            first_result = response_asc.data["results"][0]
            last_result = response_desc.data["results"][0]
            self.assertNotEqual(first_result, last_result)
