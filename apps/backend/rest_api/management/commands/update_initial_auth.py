import os
import json
from os.path import join

from django.conf import settings
from django.core.management.commands.dumpdata import Command as DumpDataCommand

initial_auth_filename = join("rest_api", "fixtures", "initial_auth.json")
temp_auth_filename = join("rest_api", "fixtures", "temp_auth.json")


class Command(DumpDataCommand):
    def handle(self, *args, **options):
        initial_auth_data = get_json_data(initial_auth_filename)
        options["exclude"] = ["auth.Permission", "auth.User"]
        options["indent"] = 2
        options["use_natural_foreign_keys"] = True
        options["use_natural_primary_keys"] = True
        options["output"] = temp_auth_filename
        super().handle("auth", *args, **options)
        data = get_json_data(temp_auth_filename)
        data = filter_groups(
            data, [*settings.PERMISSION_RELEVANT_USER_GROUPS, "admin_user"]
        )
        for dumped_group in data:
            for group in initial_auth_data:
                if dumped_group["fields"]["name"] == group["fields"]["name"]:
                    group["fields"]["permissions"] = dumped_group["fields"][
                        "permissions"
                    ]
                    break
            else:
                print(
                    f'WARNING Group "{dumped_group["fields"]["name"]}" not in initial_auth.json'
                )
        save_json_data(initial_auth_data, initial_auth_filename)
        os.unlink(temp_auth_filename)


def filter_groups(groups, relevant_groups):
    return [group for group in groups if group["fields"]["name"] in relevant_groups]


def get_json_data(filename):
    with open(filename, "r") as infile:
        data = json.load(infile)
    return data


def save_json_data(data, filename):
    with open(filename, "w") as outfile:
        json.dump(data, outfile, indent=2)
