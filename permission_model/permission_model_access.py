import json
from os.path import join


def get_json_permission_model(filename="permission_model.json"):
    with open(join("permission_model", filename), "r") as infile:
        saved_model = json.load(infile)
    return saved_model


def save_json_permission_model(permission_model, filename="permission_model.json"):
    with open(join("permission_model", filename), "w") as outfile:
        json.dump(permission_model, outfile, indent=2)


def print_admin_only_url_pattern_methods():
    model = get_json_permission_model()
    admin_only_url_patterns = []
    for url_pattern_name, url_pattern_data in model.items():
        for method_name, group_names in url_pattern_data["methods"].items():
            if ["admin_user"] == group_names:
                admin_only_url_patterns.append((url_pattern_name, method_name))
    if len(admin_only_url_patterns) > 0:
        print(
            'The following URL Pattern methods are only usable by the "admin_user" group:'
        )
        for url_pattern_name, method_name in admin_only_url_patterns:
            print(f"{url_pattern_name} --> {method_name}")
        return 1
    else:
        print('No URL Pattern methods are only usable by the "admin_user" group')
