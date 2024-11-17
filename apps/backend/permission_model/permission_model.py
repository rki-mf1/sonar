from operator import attrgetter

from django.urls import get_resolver

from permission_model.permission_model_access import get_json_permission_model
from permission_model.permission_model_access import save_json_permission_model
from rest_api import urls


def get_url_patterns():
    for resolver in get_resolver(urls).url_patterns:
        print(resolver)
        print(getattr(resolver, "name"))
    return sorted(get_resolver(urls).url_patterns, key=attrgetter("name"))


def get_url_pattern(url_pattern_name):
    l = list(
        filter(lambda p: p.name == url_pattern_name, get_resolver(urls).url_patterns)
    )
    if len(l) == 0:
        return None
    return l[0]


def get_current_permission_model():
    permission_model = {}
    for url_pattern in get_url_patterns():
        methods = {}
        for method_name in get_allowed_method_names(url_pattern):
            methods[method_name] = []
        test_kwargs = {}
        for key in get_url_kwarg_keys(url_pattern):
            test_kwargs[key] = 1
        permission_model[url_pattern.name] = {
            "pattern": str(url_pattern.pattern),
            "test_kwargs": test_kwargs,
            "test_format": "json",
            "methods": methods,
        }
    return permission_model


def get_permission_model_changes_and_errors():
    changes = []
    old_model = get_json_permission_model()
    current_permission_model_data = get_current_permission_model()
    for url_pattern_name, url_pattern_data in current_permission_model_data.items():
        if url_pattern_name not in old_model:
            changes.append(f'URL pattern "{url_pattern_name}" not in saved model')
            continue

        if "pattern" not in old_model[url_pattern_name]:
            changes.append(
                f'URL pattern "{url_pattern_name}" missing pattern in saved model'
            )
        elif url_pattern_data["pattern"] != old_model[url_pattern_name]["pattern"]:
            changes.append(f'URL pattern "{url_pattern_name}" pattern changed')

        if "test_kwargs" not in old_model[url_pattern_name]:
            changes.append(
                f'URL pattern "{url_pattern_name}" missing test_kwargs in saved model'
            )
        else:
            for key in url_pattern_data["test_kwargs"]:
                if key not in old_model[url_pattern_name]["test_kwargs"]:
                    changes.append(
                        f'URL pattern "{url_pattern_name}" missing test kwarg "{key}" in saved model'
                    )

        if "test_format" not in old_model[url_pattern_name]:
            changes.append(
                f'URL pattern "{url_pattern_name}" missing test_format in saved model'
            )

        if "methods" not in old_model[url_pattern_name]:
            changes.append(
                f'URL pattern "{url_pattern_name}" missing methods in saved model'
            )
            continue
        for method_name in url_pattern_data["methods"]:
            if method_name not in old_model[url_pattern_name]["methods"]:
                changes.append(
                    f'URL pattern "{url_pattern_name}" missing method {method_name} in saved model'
                )
            elif old_model[url_pattern_name]["methods"][method_name] == []:
                changes.append(
                    f'URL pattern "{url_pattern_name}" method "{method_name}" missing allowed groups in saved model'
                )
    return changes


def is_permission_model_changed_or_invalid():
    return len(get_permission_model_changes_and_errors()) != 0


def update_permission_model():
    old_model = get_json_permission_model()
    new_model = get_current_permission_model()
    for url_pattern_name in old_model:
        if url_pattern_name in new_model:
            for method_name in old_model[url_pattern_name]["methods"]:
                if method_name in new_model[url_pattern_name]["methods"]:
                    new_model[url_pattern_name]["methods"][method_name] = list(
                        old_model[url_pattern_name]["methods"][method_name]
                    )
            for key in old_model[url_pattern_name]["test_kwargs"]:
                new_model[url_pattern_name]["test_kwargs"][key] = old_model[
                    url_pattern_name
                ]["test_kwargs"][key]
            if "test_format" in old_model[url_pattern_name]:
                new_model[url_pattern_name]["test_format"] = old_model[
                    url_pattern_name
                ]["test_format"]
    save_json_permission_model(new_model)


def get_allowed_method_names(url_pattern):
    methods = list()
    if "view_class" in url_pattern.callback.__dict__:
        methods = list(url_pattern.callback.view_class.http_method_names)
    else:
        methods = list(url_pattern.callback.actions.keys())
    if "options" in methods:
        methods.remove("options")
    if "head" in methods:
        methods.remove("head")
    return methods


def get_url_kwarg_keys(url_pattern):
    if url_pattern is None:
        return None
    return url_pattern.pattern.regex.groupindex.keys()


def main():
    if is_permission_model_changed_or_invalid():
        update_permission_model()
        print("Model updated")
    else:
        update_permission_model()
        print("Nothing changed")
